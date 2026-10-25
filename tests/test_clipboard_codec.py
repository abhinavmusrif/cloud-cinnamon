import pathlib,subprocess,io,struct,zlib,json
from PIL import Image
import argparse,tempfile
ap=argparse.ArgumentParser()
ap.add_argument('--header',type=pathlib.Path,required=True)
s=ap.parse_args().header.resolve().parent
temporary=tempfile.TemporaryDirectory(prefix='cloud-cinnamon-codec-')
d=pathlib.Path(temporary.name)
source=r'''
#include <stdio.h>
#include "clipboard_png.h"
int main(int argc,char **argv) {
 FILE *f;long n;unsigned char *in,*out=NULL;size_t size=0;
 if(argc!=3)return 3;
 f=fopen(argv[1],"rb");if(!f)return 3;fseek(f,0,SEEK_END);n=ftell(f);rewind(f);
 in=malloc(n?n:1);if(!in)return 3;if(fread(in,1,n,f)!=(size_t)n)return 3;fclose(f);
 int ok=megas_png_to_bmp(in,n,&out,&size);free(in);
 if(!ok){if(out||size)return 4;return 2;}
 f=fopen(argv[2],"wb");if(!f)return 3;fwrite(out,1,size,f);fclose(f);free(out);return 0;
}
'''
(d/'test.c').write_text(source)
subprocess.run(['cc','-std=c99','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(s),str(d/'test.c'),'-lpng','-o',str(d/'test-codec')],check=True)
passed=[]
for w,h in [(1,1),(3,2),(1919,1080),(1920,1080),(3840,2160)]:
 image=Image.new('RGBA',(w,h),(57,128,241,255));image.putpixel((0,0),(254,17,93,255));image.putpixel((w-1,h-1),(3,7,11,255))
 image.save(d/'input.png');p=subprocess.run([str(d/'test-codec'),str(d/'input.png'),str(d/'out.bmp')],capture_output=True,text=True)
 assert p.returncode==0,(w,h,p.returncode,p.stderr)
 with Image.open(d/'out.bmp') as got:
  got.load();assert got.size==image.size;assert got.convert('RGB').tobytes()==image.convert('RGB').tobytes()
 passed.append(str(w)+'x'+str(h)+' exact RGB')
valid=(d/'input.png').read_bytes()
bad=[b'',b'not a png',valid[:8],valid[:30],valid[:-20]]
# A syntactically correct oversized IHDR must fail before allocating pixels.
ihdr=struct.pack('>IIBBBBB',100000,100000,8,6,0,0,0)
bad.append(valid[:8]+struct.pack('>I',13)+b'IHDR'+ihdr+struct.pack('>I',zlib.crc32(b'IHDR'+ihdr))+valid[33:])
for i,data in enumerate(bad):
 (d/'bad.png').write_bytes(data);p=subprocess.run([str(d/'test-codec'),str(d/'bad.png'),str(d/'bad.bmp')],capture_output=True,text=True)
 assert p.returncode==2,(i,p.returncode,p.stderr)
 passed.append('invalid input '+str(i)+' refused')
report={'passed':len(passed),'checks':passed,'sanitizers':['address','undefined'],'failures':0}
(d/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
