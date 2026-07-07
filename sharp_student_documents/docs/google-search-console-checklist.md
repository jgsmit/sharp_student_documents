# Google Search Console Checklist for SharpDocs

Use this after your production site is live.

## 1. Lock in the production domain

- Set `SITE_URL` in production to your main canonical domain, for example `https://your-live-domain.com`
- Make sure `ALLOWED_HOSTS` includes that domain
- Make sure `CSRF_TRUSTED_ORIGINS` includes the `https://` version of that domain if you use forms or admin there
- Keep one preferred hostname only, with redirects from any secondary hostnames

## 2. Verify the right Search Console property

- Add a `Domain property` if you can verify DNS
- If DNS verification is difficult, add a `URL prefix` property for the exact canonical URL in `SITE_URL`
- If you still use a temporary Render URL, verify that too until the custom domain is fully switched over

## 3. Confirm crawl basics on the live site

Open these exact paths on the live domain:

- `/robots.txt`
- `/sitemap.xml`
- `/`
- `/documents/`
- `/reviews/faq/`
- `/reviews/help-center/`
- `/reviews/contact/`

Check that:

- They load publicly without login
- They return `200 OK`
- They are not blocked by `robots.txt`
- The homepage and document list page have canonical tags

## 4. Submit the sitemap

- In Search Console, open `Sitemaps`
- Submit `https://your-live-domain.com/sitemap.xml`
- Watch for `Success` or sitemap parsing errors

## 5. Request indexing for priority pages

Request indexing for:

- Homepage
- Document list page
- 3 to 5 strong document detail pages
- FAQ page
- Help Center page
- Contact page

## 6. Check live metadata and branding

On the live site source, confirm:

- The homepage title contains `SharpDocs`
- The homepage description mentions student documents, notes, study guides, or past papers
- The homepage contains `Organization` and `WebSite` structured data
- The documents page contains `CollectionPage`, `ItemList`, and breadcrumb structured data
- The footer clearly uses the `SharpDocs` brand

Natural brand variants can appear in about or brand copy, such as:

- `SharpDoc`
- `Sharp Docs`
- `Sharp Students`
- `Sharp Student Docs`
- `SharpStudentDoc`
- `SharpStudentDocs`
- `sharp studen`

Use them naturally. Do not repeat them unnaturally across every page.

## 7. Watch indexing and coverage reports

Review:

- `Pages`
- `Sitemaps`
- `URL Inspection`
- `Enhancements`

Look for:

- `Crawled - currently not indexed`
- `Duplicate without user-selected canonical`
- `Blocked by robots.txt`
- `Alternate page with proper canonical tag`
- Soft 404s on low-content pages

## 8. Check branded discovery manually

After Google has had time to crawl, test searches like:

- `SharpDocs`
- `SharpDoc`
- `Sharp Docs`
- `Sharp Students`
- `Sharp Student Docs`
- `SharpStudentDoc`
- `SharpStudentDocs`
- `sharp studen`
- `SharpDocs notes`
- `SharpDocs past papers`
- `SharpDocs study guides`

## 9. Keep the site indexable

- Add new documents regularly
- Keep important pages linked from the homepage, footer, and navigation
- Make sure your sitemap keeps fresh URLs
- Avoid placing `noindex` on pages you want ranked
- Keep document pages descriptive, unique, and internally linked

## 10. Optional extra visibility work

- Verify Bing Webmaster Tools too
- Add consistent `SharpDocs` branding on social profiles
- Get a few real backlinks that mention `SharpDocs`
- Encourage public mentions and reviews that use the main brand name `SharpDocs`
