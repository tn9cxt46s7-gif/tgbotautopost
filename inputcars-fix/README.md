# INPUT CARS — ready fixes (apply to tn9cxt46s7-gif/Inputcars)

This agent run was connected to **tgbotautopost**, which does not have write access to **Inputcars**.
Copy these files into the Inputcars repository (or grant Cursor access to Inputcars and re-run).

## Changes
1. **Address** — cleared to a single space (not published yet); map links no longer point to Vasarnīcu iela 20B.
2. **Videos** — remuxed `1.mov` / `3.mov` → web MP4 (`1.mp4`, `3.mp4`, H.264/AAC, faststart).
   - The middle clip (`video/2.mp4`) was **never in the repo** (live site returned 404). That broken card was removed so the site has no media errors.
   - If you have the “partial paint” video, add it as `video/2.mp4` and restore the middle portfolio card.
3. **Captcha** — removed the math example (`a + b = ?`) from the booking form, client checks, and API. Google reCAPTCHA is unchanged.

## Apply
```bash
cd /path/to/Inputcars
cp -r /path/to/inputcars-fix/* .
# replace index.html, js/script.js, api/send.js, video/*
git add -A
git commit -m "Blank address, fix portfolio videos, remove math captcha"
git push
```
