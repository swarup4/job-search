# 08 — Career-page scraping

How JobPilot pulls postings straight from company career pages into `jobs` and
`job_descriptions`. This is the detailed plan behind roadmap `P3-15`…`P3-27`
([05 — Roadmap](../05-Roadmap-Backlog.md) §4). The target list is the 119 companies in the
"Job Search" sheet, each checked by hand on **2026-09-24**.

**Status:** Phases 1 and 2 built on 2026-09-25 — Workday pulls end to end. Everything after is
planned.

---

## 1. The approach

**Read the JSON the page reads, not the HTML.** A branded careers site is almost always a front
end over an applicant tracking system (ATS) or the company's own search API, and that API returns
structured postings. So each company is pulled through the cheapest tier that works, and the LLM
comes in only at the last one:

| Tier | When | How | LLM |
|---|---|---|---|
| **1. Shared ATS** | The jobs live on Workday, Oracle, Greenhouse, Lever, Eightfold… | One adapter per platform, reused across every company on it | none |
| **2. Company API** | A branded site calling its own endpoint | A small adapter per company, found once via DevTools → Network | none |
| **3. JSON-LD / HTML** | Detail pages carry a `JobPosting` block, or the list is server-rendered | One plain fetch per page | none |
| **4. Render + parse** | None of the above | Playwright renders the page, then `P3-14`'s `parse_description()` | ~1 call per job |

**Scraping itself costs nothing.** Every feed below is public and keyless, and Playwright runs
locally. There is no scraping service, proxy or CAPTCHA solver in this plan.

### How a posting is written

Tiers 1–3 already know the fields, so no LLM runs:

1. `create_job` with `source: career_page`, `refId` = the board's own requisition id,
   `listingUrl` = the apply URL
2. `create_description` with the JD converted to markdown
3. `link_description(description_id, job_id)`, which leaves it `parsed` so `parse_pending()`
   skips it

Tier 4 instead posts the rendered markdown as a `raw` description and lets `parse_description()`
write the job, with its usual checks: nothing it writes may be absent from the page.

**Dedup reuses `P3-04`.** `ingest()` sends its own `dedupHash` over `career_page|company|refId`
— the company is in the seed because two Workday tenants can both issue `R0001`. A daily re-run
gets `duplicate: true` back for every posting it already stored, and nothing is re-embedded. The
cost: a posting captured through the extension *and* scraped is stored twice.

**Filter before writing.** Accenture, Genpact, Citi, Airbus and Applied Materials each return
the 2,000-result Workday cap, and Lowe's lists 12,689. Only postings matching the target titles
and locations are written. Every write costs an embedding and, later, a match.

### Rules every adapter follows

- **robots.txt is checked on the host the jobs come from.** `DiscoveryPreferences.respect_robots`
  is `Literal[True]`, so a disallowed path is skipped rather than fetched.
- **One identifying User-Agent**, at most 2 concurrent requests per host, and backoff on 429/503.
- **Read-only.** No login, no form submit, and no apply step. Applying stays with the extension.
- **Every adapter ships with a recorded JSON fixture and a test.** Undocumented endpoints change
  without notice, and a failing fixture test is how we find out.
- **Code lives in `ai/sources/`**, one module per platform, and writes only through
  `mcp_servers/jobpilot_api/client.py`. The AI tier holds no credentials.

---

## 2. Phases

Each phase is planned and built on its own. Phase 1 is the foundation the rest share. Phases 2–7
are ordered by how many companies each one unlocks. Phase 11 goes beyond the sheet: it finds new
companies to add.

### Phase 1 — Foundation
✅ **done** (2026-09-25). Everything an adapter needs apart from its own platform logic, so the
adapter phases after it shrink to the part that differs.

**API**
- ✅ `P1-01` **`career_source` module**: one flat document per company, with `name`,
  `careersUrl`, `platform`, `config` (tenant / site / board id / host), `enabled`, `notes`,
  `lastRunAt` and `lastResult`. `GET`/`POST /career-source`, `GET`/`PATCH /career-source/{id}`,
  `PUT /career-source/result/{id}`. `Platform` gains a value only when its adapter lands, so a
  company nothing can pull cannot be registered. 6 tests in `server/tests/`
- ✅ `P1-02` `create_description`, `list_career_sources` and `record_source_result` in
  `mcp_servers/jobpilot_api/client.py`
- ✅ `P1-03` `ai/sources/http.py` — `Fetcher`: the User-Agent, 2 requests per host, backoff on
  429/503, and robots.txt checked **inside every request**, so no adapter can skip it. Every
  unclear robots answer reads as "no": only a 404 or 410 means "no file". Workday answers a
  JSON-accepting robots request with a **406**, which an earlier draft read as permission
- ✅ `P1-04` `ai/sources/base.py`: the `Posting` and `Harvest` models every adapter returns, and
  one `ingest()` that runs `create_job` → `create_description` → `link_description`. The JD is
  converted with `markdownify` and stored with `region: feed`; `htmlString` stays empty, since it
  is defined as rendered *from* the markdown. A job whose description write never landed is
  repaired on the next run rather than skipped
- ✅ `P1-05` Title and location filter from `SCRAPE_TITLES` / `SCRAPE_LOCATIONS` in `ai/.env`
  until `P4-02` gives preferences a home. Titles match on word boundaries: "AI" takes "AI / ML
  Engineer" and leaves "Maintenance Lead"
- ✅ `P1-06` `ai/sources/run.py` — `run_all()` reports fetched / matched / new / duplicate /
  failed / blocked per company and writes it to the source's `lastResult`. A 401 stops the run;
  any other refused write is counted and the run goes on

**Guardrail**
- ✅ `P1-07` 26 tests in `ai/tests/test_sources_*.py` against recorded response shapes and
  `httpx.MockTransport`. None reaches the network

### Phase 2 — Workday
🟡 **pulls end to end.** **41 companies**, the largest single win. Verified 2026-09-25 against a
throwaway database, through the Run discovery endpoint, over all 35 then-enabled companies with
`SCRAPE_TITLES=LLM`: the first run took 137s and wrote 101 linked jobs; the second took **32s**
and found all 101 already stored without fetching one detail. Citi and PwC came back `blocked`,
and one transient Workday 500 (Deutsche Bank) is now retried.

**API**
- ✅ `P2-01` `ai/sources/workday.py`: `POST /wday/cxs/{tenant}/{site}/jobs`, 20 per page (Workday
  answers 400 to more). Only the first page carries the real `total`; later ones say 0
- ✅ `P2-02` Detail fetch per wanted posting: `GET /wday/cxs/{tenant}/{site}{externalPath}` for
  the JD, `startDate`, `jobReqId`, `timeType` and the country, which is re-checked here
- 🟡 `P2-03` The country facet is found by name, nested or not, and applied to every search.
  It does not keep searches under the cap — "LLM" in India alone still reports 2,000 — so titles
  are matched locally and paging stops at the first page with none. Job-family facets not used
- ⬜ `P2-04` Shared tenants: Splunk inside Cisco, Informatica inside Salesforce and Discover
  inside Capital One are one tenant with a company-name filter, not three sources
- ✅ `P2-05` `server/career_sources_seed.json` + `seed_career_sources.py`: all 41, 33 enabled.
  Palo Alto, Lowe's, Zoom, Citi and PwC are disabled for robots — the last two were caught by the
  first full run, not by the manual check; Splunk, Informatica and Discover wait on `P2-04`. Not
  yet run against the real database

- ✅ `P2-06` Skip the detail fetch for a posting already stored. The adapter asks
  `description_stored(url)` — `GET /job-description?url=` on the local API — for every wanted
  listing, using `{origin}/{site}{externalPath}`, which is exactly the `externalUrl` stored as
  `listingUrl`. Only the rest go to Workday. Skipped postings count as `duplicate`. A tenant
  that builds the URL differently is never recognised and is fetched as before
- ⬜ `P2-07` `SCRAPE_WORKDAY_MAX_PAGES` (default 5) caps each keyword at 100 listings. Accenture's
  "LLM" filled all five pages, so its tail is cut. Raise it, or narrow with job-family facets

### Phase 3 — Oracle Recruiting Cloud
⬜ **not started.** **8 companies**, including JPMC with 7,401 jobs.

**API**
- ⬜ `P3-01` `ai/sources/oracle.py`: `GET {host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions`
  with `finder=findReqs;siteNumber={site}`, paged by `limit`/`offset`
- ⬜ `P3-02` Detail fetch for the JD (`recruitingCEJobRequisitionDetails`)
- ⬜ `P3-03` Confirm the `siteNumber` for BNY, Honeywell and Dell, which were verified by host only
- ⬜ `P3-04` Check whether American Express's `TotalJobsCount: 500` is a page cap or the real total

### Phase 4 — Greenhouse, Lever, Eightfold
⬜ **not started.** **8 companies**, and the simplest feeds on the list.

**API**
- ⬜ `P4-01` `ai/sources/greenhouse.py`: `boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`,
  which returns the JD in the list, so no detail fetch
- ⬜ `P4-02` `ai/sources/lever.py`: `api.lever.co/v0/postings/{company}?mode=json`
- ⬜ `P4-03` `ai/sources/eightfold.py`: `/api/apply/v2/jobs?domain=…` (HSBC). Qualcomm's tenant
  refuses unsigned requests, so it goes to Phase 9

### Phase 5 — Company-specific adapters
⬜ **not started.** **7 companies** that work today but share no platform.

**API**
- ⬜ `P5-01` Capgemini: `cg-jobstream-api.azurewebsites.net/api/job-search?country_code=in-en`.
  The JD comes in the list response
- ⬜ `P5-02` Mercedes-Benz: `jobs.api.mercedes-benz.com/search`. Find the India / MBRDI filter
  parameter first, since `country=IN` did not narrow it
- ⬜ `P5-03` `ai/sources/jsonld.py`: a generic `JobPosting` extractor, fed from a sitemap or
  listing page. Covers Société Générale, Bank of America and NTT Data
- ⬜ `P5-04` Server-rendered HTML lists: Birlasoft (`jobs.birlasoft.com/search`) and Intuit
  (`jobs.intuit.com` category pages; `/search-jobs/` is robots-disallowed)

### Phase 6 — Zwayam
⬜ **not started.** **5 Indian IT services companies** on one identical Angular app.

**API**
- ⬜ `P6-01` Capture the real request once in a browser (DevTools → Network). The endpoints are
  known (`public.zwayam.com/jobs-service/v1/jobs/search`), but a hand-built payload returns 400
- ⬜ `P6-02` `ai/sources/zwayam.py`, keyed by `companyId`: ITC Infotech `15154`, Happiest
  Minds `15974`; find the others the same way
- ⬜ `P6-03` Seed ITC Infotech, Happiest Minds, Cyient, Persistent and Coforge

### Phase 7 — SAP SuccessFactors
⬜ **not started.** **7 companies**, most of them large Indian employers.

**API**
- ⬜ `P7-01` Find the public job-search call the Career Site Builder front end makes. The OData
  API needs auth and is out of scope
- ⬜ `P7-02` `ai/sources/successfactors.py`. Where there's no JSON, fall back to the rendered list
  (Birlasoft's pattern in `P5-04`)
- ⬜ `P7-03` Seed Wipro, HCLTech, EY, Atos, Fujitsu and Standard Chartered. NetApp stays
  disabled because its host disallows everything

### Phase 8 — Render + parse fallback
⬜ **not started.** For the **15 companies** with no feed, plus anything a later phase gives up on.

**API**
- ⬜ `P8-01` `ai/sources/render.py`: Playwright opens the listing page, collects the detail
  links, and renders each one
- ⬜ `P8-02` HTML → markdown in Python, matching the extension's `features/capture/` rules
  (region pick, furniture stripped, links resolved) so the parser sees the same shape either way
- ⬜ `P8-03` Post as a `raw` description, then `parse_description()`, capped at N pages per
  company per run
- ⬜ `P8-04` Record the `region` and `textLength` tells. A Cloudflare or Akamai wall renders a
  near-empty page, and that has to show up in the report as blocked, not as success

**The blocked five stay blocked.** IBM, TCS, Cognizant, Fidelity and Wells Fargo answered with a
bot challenge. The plan doesn't try to get past one. Those companies are covered by the
extension's capture button instead, when you open a posting yourself.

### Phase 9 — The remaining platforms, one at a time
⬜ **not started.** **20 companies** on platforms each used by only one to three of them. Each task
is an investigation that ends in one of three outcomes: an adapter, Phase 8, or "extension capture
only".

**API**
- ⬜ `P9-01` RippleHire: LTIMindtree, Mphasis, UST. Needs a session token, so check whether the
  career site issues one anonymously
- ⬜ `P9-02` Avature: Deloitte, Tesco, Siemens. Check Deloitte's robots.txt first, since it
  ends in a catch-all `Disallow`
- ⬜ `P9-03` Phenom: Virtusa (Akamai-blocked), Snowflake, NatWest (Cloudflare; Workday
  underneath is unconfirmed)
- ⬜ `P9-04` Own apps: Goldman Sachs (only `/roles/` allowed), Walmart (`/api` disallowed),
  EPAM
- ⬜ `P9-05` Single-company platforms: Infosys (SmartDreamers), KPMG (TalentRecruit), UBS
  (PeopleFluent), Teradata (GR8 People), Schneider (Taleo), CGI (Njoyn, bot manager), Sasken
  (HireWand), Qualcomm (Eightfold, gated)

### Phase 10 — Running it
⬜ **not started.** Turning a set of adapters into something you use every day.

**API**
- ✅ `P10-01` `ai/api/` — the AI tier's own FastAPI server (`python main.py` in `ai/`, loopback,
  port 8001). `POST /api/runs/discovery/start` takes the dashboard's bearer token, checks it by asking
  the server whose it is (`getAccount`), and starts `run_all()` in the background; `GET
  /api/runs/discovery/events` streams its progress. One run at a time — a second start by the
  same account answers the running one, another account gets 409 — visible only to the
  account that started it. The token is used for that run and kept nowhere. 7 tests
- ⬜ `P10-02` Archive a job that has disappeared from its board since the last run
- ⬜ `P10-03` Mark a source `failing` after two bad runs in a row, so a changed endpoint is visible
  rather than silent

**UI**
- ⬜ `P10-04` Settings: add a company by pasting its careers URL, and see its detected platform
- ✅ `P10-05` **Run discovery** on Settings — `DiscoverySources` replaces the fixture Sources
  rail: every registered company with its last result, live per-company progress polled every
  3s, and the list re-read when the run ends. `aiInstance` shares the API instance's token,
  refresh and error handling. Polling is one request at a time, backs off to 10s, pauses in a
  hidden tab, and stops after 3 failures or 30 minutes; the AI tier caches a verified token for
  60s so a poll is an in-memory read. Each company has an on/off switch that saves at once

**Infrastructure**
- ⬜ `P10-06` Daily schedule. This is roadmap `P3-07` / `P3-12` (Redis + Celery)

### Phase 11 — Free company discovery
⬜ **not started.** Finds companies that aren't in the sheet but are hiring for your role on a
shared ATS. It reuses the Workday, Greenhouse and Lever adapters, so it can start once Phases 2
and 4 land. Numbered last only so that no id above it moves.

**How it works.** ATS feeds are per company, so there is no "search every company" call.
Common Crawl's public URL index fills that gap: querying it for every URL under an ATS domain
lists the companies on that ATS, and each URL carries the board id an adapter needs. Pulling
each board's feed then shows which of those companies are hiring for your role in India right
now. Nothing in this phase costs money. Paid search (roadmap `P3-03`) stays deferred.

**Tested on 2026-09-24.** Half of one crawl (`CC-MAIN-2026-34`) returned 203 distinct Greenhouse
boards, and the latest crawl 28 Lever boards. Workday and Ashby queries got 502s or truncated
responses: the free query API can't handle domains that large, which is why `P11-02` exists.

**API**
- ⬜ `P11-01` `ai/sources/discovery/commoncrawl.py`: query the index by ATS domain, paged with
  `showNumPages` / `page`, retrying on 502. One regex per platform extracts the board id:
  `boards.greenhouse.io/{token}` and `job-boards.greenhouse.io/{token}`, `jobs.lever.co/{company}`,
  `jobs.ashbyhq.com/{org}`, `{tenant}.wdN.myworkdayjobs.com/{site}`
- ⬜ `P11-02` Workday from the raw cc-index files, downloaded and filtered locally rather than
  through the query API. Slower, but it doesn't depend on an overloaded server
- ⬜ `P11-03` A `status` on `career_source`: `suggested`, `approved` or `rejected`. A discovered
  board is `suggested` and disabled. A rejected one is never suggested again
- ⬜ `P11-04` Probe each suggestion once: pull its feed, rate-limited, and count postings that
  pass the `P1-05` filter. A board with none is dropped. **The probe writes no jobs**
- ⬜ `P11-05` Weekly run. Common Crawl publishes about monthly, so more often than weekly finds
  nothing new

**UI**
- ⬜ `P11-06` Suggestions list in Settings: company, platform, matching count and a few sample
  titles, with **Approve** and **Reject**

**Guardrail**
- ⬜ `P11-07` Nothing discovered is scraped until you approve it. A broad crawl would otherwise
  fill `jobs` with companies you'd never apply to, each costing an embedding and a match

**What it can't find:** companies on a custom site, like Capgemini, or on a platform with no
public board URL. Those still come in by hand or through the extension's Capture button.

---

## 3. The company registry

Checked on 2026-09-24. "Jobs" is the global total the endpoint returned that day, before any
India filter. ⚠ marks a robots.txt restriction. Those rows are seeded **disabled**.

### 3.1 Workday — Phase 2 (41)

`https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`

| Company | Tenant | wd | Site | Jobs | Notes |
|---|---|---|---|---|---|
| Accenture | accenture | wd103 | AccentureCareers | 2000 | capped |
| Salesforce | salesforce | wd12 | External_Career_Site | 1503 | |
| Informatica | salesforce | wd12 | External_Career_Site | 81 | inside Salesforce; filter "Informatica" |
| Adobe | adobe | wd5 | external_experienced | 582 | |
| Workday | workday | wd5 | Workday | 371 | |
| Zendesk | zendesk | wd1 | zendesk | 116 | |
| Palo Alto Networks | paloaltonetworks | wd5 | panwexternalcareers | 1511 | ⚠ site path disallowed |
| Cisco | cisco | wd5 | Cisco_Careers | 1361 | |
| Splunk | cisco | wd5 | Cisco_Careers | — | inside Cisco; filter "Splunk" |
| Northern Trust | ntrs | wd1 | northerntrust | 650 | |
| PayPal | paypal | wd1 | jobs | 280 | |
| Fiserv | fiserv | wd5 | EXT | 358 | |
| DXC Technology | dxctechnology | wd1 | DXCJobs | 1076 | |
| Target (India) | target | wd5 | targetcareers | — | total not recorded |
| Lowe's India | lowes | wd5 | LWS_External_CS | 12689 | ⚠ site path disallowed |
| Booking Holdings | priceline | wd1 | BookingHoldings | 24 | corporate roles only |
| Airbus (India) | ag | wd3 | Airbus | 2000 | capped |
| PwC (SDC/AC) | pwc | wd3 | CRM_Experienced_Careers_Site | 1691 | ⚠ site path disallowed; allowed PwC sites list no India jobs |
| Kyndryl | kyndryl | wd5 | KyndrylProfessionalCareers | 984 | also `KyndrylEarlyCareers` |
| Genpact | genpact | wd108 | External_Careers | 2000 | capped |
| State Street | statestreet | wd1 | Global | 1348 | |
| Citi | citi | wd5 | 2 | 2000 | ⚠ robots.txt disallows `/2/` — the site id itself |
| Discover | capitalone | wd12 | Capital_One | 1812 | now Capital One; filter by brand |
| Invesco | invesco | wd1 | IVZ | 245 | |
| Morgan Stanley | ms | wd5 | External | 1319 | |
| Deutsche Bank | db | wd3 | DBWebsite | 1161 | |
| Barclays | barclays | wd3 | External_Career_Site_Barclays | 826 | Pune 249, Gurugram 44 |
| Visa | visa | wd5 | Visa | 799 | |
| Mastercard | mastercard | wd1 | CorporateCareers | 1063 | Pune 185, Gurgaon 44 |
| Collins Aerospace | globalhr | wd5 | REC_RTX_Ext_Gateway | 4808 | RTX-wide; filter by business unit |
| Applied Materials | amat | wd1 | External | 2000 | capped |
| Expedia Group | expedia | wd108 | search | 168 | |
| Rakuten | rakuten | wd1 | RakutenAsia | 30 | ~24 regional sites |
| Intel | intel | wd1 | External | 616 | |
| Philips | philips | wd3 | jobs-and-careers | 856 | |
| HPE | hpe | wd5 | Jobsathpe | 1280 | |
| CrowdStrike | crowdstrike | wd5 | crowdstrikecareers | 373 | |
| Zoom | zoom | wd5 | Zoom | 91 | ⚠ site path disallowed |
| Autodesk | autodesk | wd1 | Ext | 377 | |
| BrowserStack | browserstack | wd3 | External | 35 | |
| Genesys | genesys | wd1 | Genesys | 204 | |

### 3.2 Oracle Recruiting Cloud — Phase 3 (8)

`{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?finder=findReqs;siteNumber={site}`

| Company | Host | Site | Jobs | Notes |
|---|---|---|---|---|
| JPMorgan Chase | jpmc.fa.oraclecloud.com | CX_1001 | 7401 | |
| American Express | egug.fa.us2.oraclecloud.com | CX_1 | 500 | may be a cap |
| BNY | eofe.fa.us2.oraclecloud.com | BNY-Careers | 1395 | confirm `siteNumber` |
| Texas Instruments | edbz.fa.us2.oraclecloud.com | CX | 770 | |
| Honeywell | ibqbjb.fa.ocs.oraclecloud.com | — | 1320 | confirm `siteNumber` |
| Dell | enterpriseplatform.dell.com | — | 461 | confirm `siteNumber` |
| Hexaware | fa-etqo-saasfaprod1.fa.ocs.oraclecloud.com | CX_1 | 301 | |
| Zensar | fa-etvl-saasfaprod1.fa.ocs.oraclecloud.com | CX_1 | 292 | |

### 3.3 Greenhouse, Lever, Eightfold — Phase 4 (8)

| Company | Platform | Board / endpoint | Jobs |
|---|---|---|---|
| HubSpot | Greenhouse | `hubspotjobs` | ✓ |
| Okta | Greenhouse | `okta` | ✓ |
| Datadog | Greenhouse | `datadog` | ✓ |
| Thoughtworks | Greenhouse | `thoughtworks` | 37 (3 India) |
| New Relic | Greenhouse | `newrelic` | 52 |
| Zscaler | Greenhouse | `zscaler` | 372 |
| Coupa | Lever | `coupa` | 27 |
| HSBC | Eightfold | `portal.careers.hsbc.com/api/apply/v2/jobs?domain=hsbc.com` | 1596 |

### 3.4 Company-specific — Phase 5 (7)

| Company | Kind | Endpoint | Jobs |
|---|---|---|---|
| Capgemini | own API | `cg-jobstream-api.azurewebsites.net/api/job-search` | 920 India |
| Mercedes-Benz R&D | own API | `jobs.api.mercedes-benz.com/search` | 2650 global |
| Société Générale | JSON-LD | `careers.societegenerale.com/en/job-offers/…` | — |
| Bank of America | JSON-LD | `careers.bankofamerica.com/en-us/job-detail/{id}/…` | — |
| NTT Data | JSON-LD | `careers.nttdata.com/global/en/job/{id}/…` | — |
| Birlasoft | HTML list | `jobs.birlasoft.com/search/` | 28 |
| Intuit | HTML list | `jobs.intuit.com` category pages | — |

### 3.5 Platform known, feed not pulled yet — Phases 6, 7, 9 (32)

| Platform | Companies | Phase |
|---|---|---|
| Zwayam | ITC Infotech, Happiest Minds, Cyient, Persistent Systems, Coforge | 6 |
| SAP SuccessFactors | Wipro, HCLTech, EY (GDS), Atos, Fujitsu, Standard Chartered, NetApp ⚠ | 7 |
| RippleHire | LTIMindtree (incl. Mindtree), Mphasis, UST | 9 |
| Avature | Deloitte (USI) ⚠, Tesco (HSC), Siemens | 9 |
| Phenom | Virtusa, Snowflake, NatWest Group | 9 |
| Own app | Goldman Sachs ⚠, Walmart Global Tech ⚠, EPAM Systems | 9 |
| Single-company | Infosys, KPMG, UBS, Teradata, Schneider Electric, CGI, Sasken, Qualcomm | 9 |

### 3.6 Render + parse only — Phase 8 (15)

| Why | Companies |
|---|---|
| Bot challenge (Cloudflare / Akamai / 403) | IBM India, TCS, Cognizant, Fidelity, Wells Fargo, GlobalLogic |
| No ATS signature found | Atlassian, Tech Mahindra, EXL, Microland, Sony India Software, Publicis Sapient, Clari, Whatfix, Sonata Software |

### 3.7 Blocked by robots.txt — seeded disabled (7)

| Company | What robots.txt says |
|---|---|
| ServiceNow, Bosch, Sopra Steria, Western Digital, Nagarro, T-Systems, Freshworks | `api.smartrecruiters.com` disallows every crawler except LinkedInBot |

The API answers for all seven, with 684, 4810, 2009, 330, 892, 76 and 123 jobs. The adapter
would take an afternoon, but the rule is fixed, so they're out until §4 decides otherwise.

**Total:** 41 + 8 + 8 + 7 + 32 + 15 + 7 = 118, plus Mindtree, which is folded into LTIMindtree.

---

## 4. Open decisions

1. **The 14 robots-restricted companies**: the 7 SmartRecruiters companies, Palo Alto, Lowe's,
   Zoom, NetApp, Deloitte, Goldman Sachs and Walmart. Either skip them, or cover them only through
   the extension's capture button, where a human opens the page. The plan assumes the second.
2. ~~**How a run is triggered.**~~ **Settled 2026-09-25:** an AI-tier endpoint that receives the
   forwarded JWT (`P10-01`). Still open for the scheduled run in `P3-07`, which has no browser to
   forward a token from. A run also inherits the access token's 60-minute life; `P2-06` keeps
   re-runs short enough that this should not bite.
3. ~~**Where the title and location filter lives.**~~ **Settled 2026-09-26:** saved per account
   through `/api/preference` from the Settings screen; each run reads it once at the start.
4. **Whether the per-platform count justifies Phase 9 at all**, versus sending those 20 companies
   straight to Phase 8 or to extension capture.
