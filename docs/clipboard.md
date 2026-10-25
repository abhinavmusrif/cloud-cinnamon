# Clipboard engineering and troubleshooting

## Image transfer

Windows screenshots commonly expose Bitmap, CF_DIB and CF_DIBV5. On the original
1920×1080 desktop, uncompressed transfer was about 8.3 MB and a Linux BMP request
took 8.9 seconds. That coincided with the RDP-only stalls; the machine had ample
free memory and idle CPU.

The Windows helper preserves these native formats and adds registered `PNG`
only for a plain image clipboard. The patched xrdp channel recognizes the
registered format ID and sends PNG instead of DIB when available. Linux
applications requesting BMP get a locally decoded top-down 24-bit BMP.

The patch includes bounded decoding, generation checks, explicit rejection of
overlapping requests and unsupported text requests, and a 1.2-second bitmap
announcement coalescing window for PNG to arrive. Non-PNG clients retain the
ordinary bitmap fallback. Bounds are 64 MB of PNG/BMP data and 16,384 pixels per
dimension; the Windows helper additionally limits source images to 32 megapixels.
Images exceeding these limits are not promised to transfer.

PNG usually reduced the measured screenshot payload to about 0.7 MB. Original
live tests covered PNG, legacy BMP, GTK image consumers and concurrent requests.
Those results describe that desktop, not a throughput guarantee for every cloud
connection. CPU encoding and network latency still matter.

## Linux text in Win+V

mstsc can expose Linux text for ordinary paste while marking it ineligible for
Windows clipboard history. With `-EnableTextHistory`, a supervised one-shot
worker materializes bounded ordinary text, permits local history and sets
`CanUploadToCloudClipboard=0`. It preserves explicit
`ExcludeClipboardContentFromMonitorProcessing` exclusions, skips unknown mixed
formats, avoids duplicates, and checks the sequence before replacing clipboard
data. A timeout stops delayed rendering from blocking the image helper.

Opt in only if you want remote text retained locally. The code does not enable
history, clear your history, log clipboard text, persist text to files, or enable
cloud clipboard sync. Password managers and applications must mark sensitive
clipboard content correctly; no generic text classifier can guarantee secrecy.

Format semantics:
[Microsoft clipboard formats](https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-formats).

## Regression checklist

Use synthetic content, not real credentials or documents:

1. Copy a multiline Unicode string from Windows; paste into Linux Terminal using
   Ctrl+Shift+V. Compare punctuation, line breaks, Hindi/Telugu/emoji if relevant.
2. Copy text from Linux; paste into Windows. With history enabled and opted in,
   verify the same text appears once in Win+V. Local Windows text must still work.
3. Copy/select a Windows screenshot; Ctrl+V into Linux Writer. Confirm dimensions
   and appearance, and scroll/touch the RDP session during the transfer.
4. Repeat image → text → image quickly; a late response must not replace a newer
   copy. Test a local-only rich text/file clipboard without altering its formats.
5. Reconnect and repeat. Inspect helper status logs without recording contents.

Terminal Ctrl+V is not the GUI paste shortcut. Win+PrintScreen's file saving,
clipboard/history eligibility and selecting a history item are Windows behavior
outside this helper. The kit does not take screenshots automatically.

If images fail, confirm `redirectclipboard:i:1`, the patched channel is active
after a fresh login, the Windows helper is running with `-STA`, and Linux Writer
can accept images. If the whole session freezes, inspect RDP/transport logs and
CPU/memory rather than assuming clipboard or GPU is always the cause.
