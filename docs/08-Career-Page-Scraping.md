# 08 — Career-page scraping

How JobPilot pulls postings straight from company career pages into `jobs` and
`job_descriptions`, and which companies it pulls from. The target list is the 119 companies in
the "Job Search" sheet, each checked by hand on **2026-09-24**.

**The tasks and their status are not here.** They are roadmap **Phase 12** —
[05 — Roadmap](../05-Roadmap-Backlog.md#13-phase-12--career-page-scraping) — moved there on 2026-11-10. This document keeps the approach and the registry the stages are sized from.

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
| **4. Render + parse** | None of the above | Playwright renders the page, then roadmap `P3-14`'s `parse_description()` | ~1 call per job |

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

## 2. The company registry

Checked on 2026-09-24. "Jobs" is the global total the endpoint returned that day, before any
India filter. ⚠ marks a robots.txt restriction. Those rows are seeded **disabled**.

### 2.1 Workday — Stage 2 (41)

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

### 2.2 Oracle Recruiting Cloud — Stage 3 (8)

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

### 2.3 Greenhouse, Lever, Eightfold — Stage 4 (8)

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

### 2.4 Company-specific — Stage 5 (7)

| Company | Kind | Endpoint | Jobs |
|---|---|---|---|
| Capgemini | own API | `cg-jobstream-api.azurewebsites.net/api/job-search` | 920 India |
| Mercedes-Benz R&D | own API | `jobs.api.mercedes-benz.com/search` | 2650 global |
| Société Générale | JSON-LD | `careers.societegenerale.com/en/job-offers/…` | — |
| Bank of America | JSON-LD | `careers.bankofamerica.com/en-us/job-detail/{id}/…` | — |
| NTT Data | JSON-LD | `careers.nttdata.com/global/en/job/{id}/…` | — |
| Birlasoft | HTML list | `jobs.birlasoft.com/search/` | 28 |
| Intuit | HTML list | `jobs.intuit.com` category pages | — |

### 2.5 Platform known, feed not pulled yet — Stages 6, 7, 9 (32)

| Platform | Companies | Stage |
|---|---|---|
| Zwayam | ITC Infotech, Happiest Minds, Cyient, Persistent Systems, Coforge | 6 |
| SAP SuccessFactors | Wipro, HCLTech, EY (GDS), Atos, Fujitsu, Standard Chartered, NetApp ⚠ | 7 |
| RippleHire | LTIMindtree (incl. Mindtree), Mphasis, UST | 9 |
| Avature | Deloitte (USI) ⚠, Tesco (HSC), Siemens | 9 |
| Phenom | Virtusa, Snowflake, NatWest Group | 9 |
| Own app | Goldman Sachs ⚠, Walmart Global Tech ⚠, EPAM Systems | 9 |
| Single-company | Infosys, KPMG, UBS, Teradata, Schneider Electric, CGI, Sasken, Qualcomm | 9 |

### 2.6 Render + parse only — Stage 8 (15)

| Why | Companies |
|---|---|
| Bot challenge (Cloudflare / Akamai / 403) | IBM India, TCS, Cognizant, Fidelity, Wells Fargo, GlobalLogic |
| No ATS signature found | Atlassian, Tech Mahindra, EXL, Microland, Sony India Software, Publicis Sapient, Clari, Whatfix, Sonata Software |

### 2.7 Blocked by robots.txt — seeded disabled (7)

| Company | What robots.txt says |
|---|---|
| ServiceNow, Bosch, Sopra Steria, Western Digital, Nagarro, T-Systems, Freshworks | `api.smartrecruiters.com` disallows every crawler except LinkedInBot |

The API answers for all seven, with 684, 4810, 2009, 330, 892, 76 and 123 jobs. The adapter
would take an afternoon, but the rule is fixed, so they're out until the roadmap's Phase 12 open
decisions say otherwise.

**Total:** 41 + 8 + 8 + 7 + 32 + 15 + 7 = 118, plus Mindtree, which is folded into LTIMindtree.

---
