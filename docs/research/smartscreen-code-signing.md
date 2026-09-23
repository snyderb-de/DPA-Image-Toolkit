# What it takes for a Windows EXE to stop triggering SmartScreen

Research note for `P2-W2-E1-024`. Researched 2026-09-18.

Context this was written against: `image-toolkit.exe` is a PyInstaller one-file EXE
of roughly 80 MB, distributed to a handful of staff from `X:\Apps\image-toolkit.exe`
on a network share, already signed with an enterprise key at the share (see
`docs/adr/0002-code-signing-at-the-share.md`). Download volume is very low. Several
of the mechanisms below only work at scale, and that is called out each time.

## How to read this

Every claim is traced to the document that owns it. Sources are ranked:

- **Primary, normative** — CA/Browser Forum Baseline Requirements, Microsoft Trusted
  Root Program requirements, Microsoft Learn product documentation.
- **Primary, non-normative** — Microsoft Q&A answers written by Microsoft employees,
  archived Microsoft blog posts. Useful, but not documentation, and Microsoft does not
  treat them as commitments.
- **Not used** — blog posts, CA marketing pages, and AI-generated Microsoft Q&A
  answers. Where an AI-generated Q&A answer is quoted below it is labelled as such and
  is never the sole basis for a claim.

Where two Microsoft pages contradict each other, both are quoted. That happens more
than once; see [Where the sources disagree](#where-the-sources-disagree).

---

## 1. Does code signing alone clear SmartScreen?

**No. Signing and reputation are separate mechanisms, and signing does not confer
reputation.**

SmartScreen evaluates two signals, and Microsoft names them explicitly:

> SmartScreen evaluates two signals when a user downloads and runs a file:
> 1. **Publisher reputation** — Is the file signed? Is the signing certificate from a known, trusted publisher?
> 2. **File hash reputation** — Has this specific file been downloaded by users without indications of malicious behavior?
>
> A negative or unknown reputation for a file's hash or its publisher's certificate can
> cause warnings to show. Even when signed, a newly created binary could still show a
> SmartScreen warning until its hash or publisher certificate accumulates sufficient
> evidence of positive reputation.

— [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) (`ms.date` 2026-05-04, page updated 2026-08-17)

The same page's certificate table is blunt about what a valid certificate buys on first
download:

| Certificate type | First-download SmartScreen behavior |
| --- | --- |
| Microsoft Store | ✅ No warning — covered by Microsoft's certificate |
| Valid Certificate (OV/EV) | ⚠️ Warning — app flagged as unrecognized until reputation accumulates; verified publisher name is displayed |
| No signature | ⚠️ Warning — "Windows protected your PC"; User must choose "Run anyway" before the app can run. Enterprise policy can prevent continuation entirely. |
| Self-signed Certificate | ⚠️ Warning — Same behavior as no signature |

— same page

### What signing does buy

1. **The publisher name appears in the dialog** instead of an unknown publisher. The
   table above: "verified publisher name is displayed".
2. **A vehicle for reputation to accumulate across releases.** Unsigned files cannot
   inherit anything: "When a file is not signed, SmartScreen reputation must build for
   each new version of your files, starting with zero reputation. Reputation cannot
   transfer from previous versions unless both were signed using the same publisher
   identity." ([same page](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation))
3. **Eligibility under Smart App Control**, which is a different feature and a harder
   gate. Smart App Control "will still allow an app to run if it is signed with a
   certificate issued by a certificate authority (CA) within the Trusted Root Program",
   and "Malware, Potentially Unwanted Apps (PUA), and unknown, unsigned code are blocked
   by default" ([Smart App Control overview](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview)).
   Note the requirement is a CA *in the Trusted Root Program* — a private enterprise CA
   does not satisfy this.

### What signing does not buy

Nothing about the prompt on a brand-new build. A freshly built EXE has a hash nobody has
ever seen, and the certificate signal is only as good as the certificate's accumulated
history. A **self-signed certificate is explicitly equivalent to no signature** for
SmartScreen purposes (table above), which matters if the "enterprise key" in use chains
to an internal CA rather than a publicly trusted one.

One more mechanical detail that bites PyInstaller builds: **every build is a new hash**,
so hash reputation restarts every release regardless of signing. Only the certificate
signal can carry over.

---

## 2. OV vs EV certificates — is the "EV grants instant reputation" claim still true?

**No. It was true, Microsoft said so in writing, and it was withdrawn in 2024. The
current Microsoft wording is not vague — it is an explicit retraction.**

### What Microsoft originally said (2012)

> Programs signed by an EV code signing certificate can immediately establish reputation
> with SmartScreen reputation services even if no prior reputation exists for that file
> or publisher.

— Jeb Haber, Lead Program Manager, SmartScreen, [Microsoft SmartScreen & Extended Validation (EV) Code Signing Certificates](https://learn.microsoft.com/en-us/archive/blogs/ie/microsoft-smartscreen-extended-validation-ev-code-signing-certificates) (2012-08-14)

That post is still online. It carries `is_archived: true` and `ROBOTS: NOINDEX,NOFOLLOW`
in its metadata, but it has **not** been edited or annotated to say the behaviour was
removed. It is a significant reason stale advice persists. The same post also claimed EV
certificates "have a unique identifier which makes it easier to maintain reputation
across certificate renewals" — that identifier was the EV OID, and see below for what
happened to it.

Microsoft repeated the claim as late as 2021 in a Microsoft Q&A answer, quoting CA
marketing verbatim: "An EV code signing certificate offers an immediate reputation with
Microsoft SmartScreen, so your users will never have to click through a SmartScreen
warning in Windows" ([Microsoft Q&A, answered 2021-06-07](https://learn.microsoft.com/en-us/answers/questions/417016/reputation-with-ov-certificates-and-are-ev-certifi)).

### What changed, and the normative source

The governing change is in the Microsoft Trusted Root Program requirements, section
"Code Signing Root Certificate Requirements":

> Starting February 2024, Microsoft will no longer accept or recognize EV Code Signing
> Certificates, and CCADB will cease to accept EV Code Signing Audits. Beginning in
> August 2024, all EV Code Signing OIDs will be removed from existing roots in the
> Microsoft Trusted Root Program, and all Code Signing certificates will be treated
> equally.

— [Program Requirements — Microsoft Trusted Root Program](https://learn.microsoft.com/en-us/security/trusted-root/program-requirements), §3.D.3

**Caveat on that citation.** That Learn page now carries the note "This page has been
superceded. The program technical requirements can be found here:
https://github.com/TrustedRootProgram/Program-Requirements". The current
[`Requirements.md`](https://github.com/TrustedRootProgram/Program-Requirements/blob/main/Requirements.md)
in that repository no longer contains the February/August 2024 sentence — it has been
dropped as a spent transition clause, not reversed. The EKU tables there still list "EV
Code Signing" as an audit/EKU category, so the term has not disappeared entirely from
the program; what disappeared is the OID in the roots and the differentiated treatment.

### Current Microsoft wording

> **EV certificates no longer bypass SmartScreen.** Years ago, signing files with an
> Extended Validation (EV) code signing certificate would result in positive SmartScreen
> reputation by default, but this behavior no longer exists. EV certificates may matter
> for enterprise procurement, but they no longer impact SmartScreen behavior. Paying a
> premium for EV solely to avoid SmartScreen warnings is no longer justified.

— [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

> **Status: Behavior changed in 2024.** Prior to 2024, Extended Validation (EV) code
> signing certificates granted immediate SmartScreen reputation — a newly-signed binary
> would show no download warning. Microsoft updated the Trusted Root Program requirements
> in 2024, removing EV-specific OIDs. SmartScreen reputation now **accumulates over time**
> rather than being granted instantly by certificate type. […] no certificate type (OV or
> EV) grants an immediate bypass.

— [Current status of Windows app distribution features](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/distribution-feature-status) (last reviewed August 2026)

> **EV certificate** | $400+/year | Worldwide | ⚠️ Same as OV since 2024 — no longer
> instant bypass | ❌ No | No longer recommended specifically for SmartScreen bypass

— [Code signing options for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) (`ms.date` 2026-08-29)

So: **withdrawn, not vaguer.** Microsoft's current guidance is more explicit than at any
point since 2012. The remaining documented differences between OV and EV are identity
vetting rigour and procurement optics, not SmartScreen behaviour.

---

## 3. Azure Trusted Signing — now "Azure Artifact Signing"

**The service was renamed.** Documentation now lives under
[`/azure/artifact-signing/`](https://learn.microsoft.com/en-us/azure/artifact-signing/overview)
and the product is "Azure Artifact Signing (formerly Trusted Signing)"; before that it was
"Azure Code Signing". Several Microsoft Learn pages still link to the old
`/azure/trusted-signing/` path, the Azure DevOps task is now `AzureArtifactSigning@<version>`,
and the Azure CLI extension is `artifact-signing` ([Artifact Signing FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq),
[Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart)). Expect
to hit all three names when searching.

### Availability

Two current Microsoft pages give **different country lists**:

- [Quickstart: Set up Artifact Signing](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) (page updated 2026-09-18):
  > Public Trust certificates are available to organizations in the United States, Canada,
  > the European Union, the United Kingdom, Australia, New Zealand, Japan, South Korea,
  > Singapore, Switzerland, Norway, and Israel. Individual developers must be located in
  > the United States or Canada. These geographic restrictions do not apply to Private
  > Trust certificates.
- [Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) (`ms.date` 2026-08-29):
  > **Geographic limitation:** Azure Artifact Signing is available to organizations in the
  > USA, Canada, the European Union, and the United Kingdom. Individual developers are
  > currently limited to the USA and Canada.

The quickstart is the more recently updated and more specific page, and is the one the FAQ
points at for the supported-region list. Both lists include the EU, so this ambiguity does
not affect a German organisation.

### Eligibility — the organisation-age requirement

This is the area where stale advice is worst, because the requirement **was real, was
documented, was tightened, and now appears to be gone without a published retraction.**

- **Historical, verbatim.** The Trusted Signing quickstart as archived on 2024-07-26 stated,
  in the "Important information for public identity validation" table:
  > Trusted Signing at this time can onboard only legal business entities that have
  > verifiable tax history of three or more years.

  — [Wayback snapshot, 2024-07-26](https://web.archive.org/web/20240726101000/https://learn.microsoft.com/en-us/azure/trusted-signing/quickstart)
- **Tightened in 2025.** Microsoft's [Trusted Signing Public Preview Update](https://techcommunity.microsoft.com/blog/microsoft-security-blog/trusted-signing-public-preview-update/4399713)
  announced a further restriction effective 2 April 2025 limiting new subscriptions to
  US- and Canada-based organisations with three or more years of verifiable history, with
  onboarding closed to individual developers and all other organisations for the remainder
  of the preview. *(I could not retrieve this post's body directly — it renders client-side —
  so this is sourced from the search index summary of that Microsoft-authored page, not from
  the page text itself. Treat the exact wording as unverified; the existence and direction of
  the restriction is corroborated by the archived quickstart above and by the current docs
  having relaxed since.)*
- **Current documentation contains no age requirement.** The same table in the
  [current quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart)
  now reads only: "For a quicker onboarding process, ensure that public records for the
  legal business entity that you're validated are up to date." The tax-history sentence is
  gone. The listed prerequisites are a Microsoft Entra tenant ID and an Azure subscription,
  plus the geographic restrictions above.
- **Microsoft has confirmed this in Q&A.** Asked directly whether a US LLC formed in 2025
  is eligible under GA, Meha-MSFT (identified as a Microsoft employee) answered on
  2026-08-17: "Artifact Signing has country/region onboarding pre-reqs, no minimum org age
  restrictions."
  ([Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5977141/azure-artifact-signing-trusted-signing-is-a-us-llc)).
  The top-voted community answer on that same thread is AI-generated and asserts the
  opposite; it is wrong, and it is a good illustration of how the stale claim propagates.

**Conclusion:** the three-year requirement appears to have been dropped, evidenced by its
removal from the documentation plus an on-record Microsoft employee statement. Microsoft has
not published a change note saying so, so verify before committing budget.

Other hard eligibility facts:

- **No free, trial, or sponsored Azure subscriptions.** "To create an Artifact Signing
  account and certificate profiles, you must have a paid Azure subscription."
  ([FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq))
- **Identity validation takes 1–20 business days**, longer if extra documentation is
  requested, with only three documentation attempts allowed. Validation also expires and
  must be renewed or certificate renewal — and therefore signing — stops.
  ([Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart),
  [FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq))

### Pricing

Microsoft's public pricing page renders its numbers client-side and returns placeholders to
a plain fetch. The authoritative machine-readable figures come from Microsoft's own Azure
Retail Prices API (`https://prices.azure.com/api/retail/prices`, `serviceName` still
`Trusted Signing`), queried 2026-09-18:

| SKU | Price | Included quota |
| --- | --- | --- |
| Basic account | **$9.99 / month** | 5,000 signatures/month, 1 certificate profile of each type |
| Premium account | **$99.99 / month** | 100,000 signatures/month, 10 certificate profiles of each type |
| Signature overage | **$0.005 / signature** | — |

Quotas and profile counts from the
[Artifact Signing pricing page](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/);
prices from the Retail Prices API. Microsoft Learn independently states "Starts at
$9.99/month" ([SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation))
and "Approximately $9.99/month" ([Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)),
which corroborates the Basic tier.

Billing is **not pro-rated**: "The invoice is generated with the full amount for the SKU
that you selected when you created the account, regardless of when you begin to use the
service" ([FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)).

### Does it confer SmartScreen reputation?

**No, and Microsoft says so directly.**

> **SmartScreen behavior:** New files can show a SmartScreen warning until they accumulate
> sufficient reputation. Azure Artifact Signing does **not** provide instant SmartScreen
> trust, but signing consecutive releases with a consistent publisher/signing identity lets
> publisher reputation build over time, so later releases can inherit trust.

— [Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)

> SmartScreen reputation builds up automatically. The prompt stops appearing once the file
> hash has sufficient download history.

— [Artifact Signing FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)

Artifact Signing **does not and will not issue EV certificates**: "No, Artifact Signing
doesn't issue Extended Validation (EV) certificates. There's no plan to issue EV
certificates in the future." ([FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq))

### The part that matters and is under-documented: short-lived certificates

> To help reduce the impact of signing misuse and abuse, Artifact Signing certificates are
> renewed daily and are valid for only 72 hours.

> Due to Artifact Signing's *daily certificate renewal*, pinning trust or validation to an
> end-entity certificate that uses certificate attributes (for example, the public key) or
> a certificate's *thumbprint* (the hash of the certificate) isn't durable. […] To address
> these issues, Artifact Signing provides a durable identity value in each certificate […]
> a custom EKU that has the prefix `1.3.6.1.4.1.311.97.`

— [Artifact Signing certificate management](https://learn.microsoft.com/en-us/azure/artifact-signing/concept-certificate-management)

Because of this, RFC 3161 timestamping is mandatory in practice, and Microsoft provides a
TSA at `http://timestamp.acs.microsoft.com` which it recommends all subscribers use (same
page). Keys live in FIPS 140-3 Level 3 HSMs and **cannot be exported**: "Artifact Signing
does *not* support importing or exporting private keys and certificates" (same page); "The
Authenticode certificate that's used for signing with the profile is never given to you"
([FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)).

**Unverified gap:** Microsoft documents that the end-entity thumbprint rotates daily and
that a durable identity EKU exists for trust pinning (specifically naming WDAC/CI policy as
the consumer). It does **not** document whether SmartScreen's publisher-reputation signal
keys on that durable EKU, on the intermediate CA, on the subject DN, or on the thumbprint.
If it keys on the thumbprint, per-certificate reputation could not accumulate for an
Artifact Signing publisher at all. I could not resolve this from any primary source, and I
am not asserting either way. There is at least one 2026 user report of an Artifact Signing
customer seeing SmartScreen warnings return after an intermediate CA change
([Microsoft Q&A, 2026-04-16](https://learn.microsoft.com/en-us/answers/questions/5861538/azure-trusted-signing-still-seeing-smartscreen-war));
the only answer on that thread is AI-generated and cites nothing, so it corroborates the
symptom being reported but not the explanation.

---

## 4. CA/Browser Forum hardware key-storage requirements

### The governing document

[Baseline Requirements for the Issuance and Management of Publicly-Trusted Code Signing
Certificates](https://cabforum.org/working-groups/code-signing/requirements/), **version
3.11.0, dated 16 June 2026**, adopted by ballot CSCWG-32. PDF:
[`CA-Browser-Forum-CSCBR-3.11.0.pdf`](https://cabforum.org/uploads/CA-Browser-Forum-CSCBR-3.11.0.pdf).
The key-storage text below is **byte-identical between v3.8.0 (August 2024) and v3.11.0** —
I diffed both — so nothing in this area has moved recently.

### Scope: this does not apply to internal enterprise PKI

> These Requirements do not address the issuance, use, maintenance, or revocation of
> Certificates by enterprises that operate their own Public Key Infrastructure for internal
> purposes only, where the Root CA Certificate is not distributed by any Application
> Software Supplier.

— CSBR v3.11.0 §1.1

**Directly relevant to us.** If the "enterprise key" signing the toolkit chains to an
internal CA, none of the hardware rules below bind it — and equally, the certificate is not
publicly trusted, so SmartScreen treats it as self-signed on any machine that does not trust
that root, and Smart App Control will not accept it at all.

### What is actually required

The current rule, **effective 1 June 2023** (CSBR v3.11.0 §6.2.7.4.1):

> Effective June 1, 2023, Subscriber Private Keys for Code Signing Certificates SHALL be
> protected per the following requirements. The CA MUST obtain a contractual representation
> from the Subscriber that the Subscriber will use one of the following options to generate
> and protect their Code Signing Certificate Private Keys in a Hardware Crypto Module with a
> unit design form factor certified as conforming to at least FIPS 140‑2 Level 2 or Common
> Criteria EAL 4+:
>
> 7. Subscriber uses a Hardware Crypto Module meeting the specified requirement;
> 8. Subscriber uses a cloud‑base key generation and protection solution with the following requirements:
>    1. Key creation, storage, and usage of Private Key must remain within the security boundaries of the cloud solution's Hardware Crypto Module that conforms to the specified requirements;
>    2. Subscription at the level that manages the Private Key must be configured to log all access, operations, and configuration changes on the resources securing the Private Key.
> 9. Subscriber uses a Signing Service which meets the requirements of Section 6.2.7.3.

Two things people commonly get wrong:

- **The bar is FIPS 140-2 Level 2, not Level 3** — for *subscribers*. Signing Services face
  a higher bar: "For Code Signing Certificates, Signing Services SHALL protect Subscriber
  Private Keys in a Hardware Crypto Module conforming to at least FIPS 140‑2 level 3 or
  Common Criteria EAL 4+" and "A Signing Service MUST enforce multi‑factor authentication or
  server‑to‑server authentication to access and authorize Code Signing" (§6.2.7.3).
- **The pre-2023 rules were laxer and are still widely quoted.** Before 1 June 2023, non-EV
  subscribers could use a TPM, a certified module, *or* "another type of hardware storage
  token with a unit design form factor of SD Card or USB token (not necessarily certified as
  conformant with FIPS 140‑2 Level 2 or Common Criteria EAL 4+)" — with a warranty to keep it
  "physically separate from the device that hosts the code signing function until a signing
  session is begun" (§6.2.7.4.1, options 1–3). That option is gone.

§6.2.7.4.2 then requires the CA to *verify* compliance by one of seven methods — key
attestation, CA-shipped module, CA-prescribed library, internal or external IT audit, a
report from the cloud key-protection subscription, an approved auditor witnessing key
creation, or "The Subscriber provides an agreement that they use a Signing Service meeting
the requirements of Section 6.2.7.3."

A "Signing Service" is defined as "An organization that generates the Key Pair and securely
manages the Private Key associated with a Code Signing Certificate, on behalf of a
Subscriber" (CSBR §1.6.1 definitions).

Also worth knowing: **code signing certificate validity must not exceed 39 months** (§6.3.2).

### What this means for CI automation

The three permitted routes have very different automation stories:

| Route | CI automation story |
| --- | --- |
| **§6.2.7.4.1(7)** — subscriber-held HSM / USB token | Effectively un-automatable on hosted CI runners. A physical token cannot be attached to a GitHub-hosted runner. Requires a self-hosted Windows runner with the token plugged in and a way to supply the token PIN unattended, which most token vendors deliberately make awkward. |
| **§6.2.7.4.1(8)** — cloud key generation and protection | Automatable. The key lives in a cloud HSM (Azure Key Vault Managed HSM and equivalents); CI authenticates to the vault and calls a remote signing operation. Note the *mandatory* second clause: the subscription must log all access, operations, and configuration changes on the key resources. That is a compliance obligation on you, not just a suggestion. |
| **§6.2.7.4.1(9)** — a Signing Service | Automatable, and the least work. The service holds the key; CI holds only a credential. Azure Artifact Signing is one such service and is explicitly designed around this — "No hardware token required: Signing integrates directly with CI/CD pipelines (GitHub Actions, Azure DevOps, and others) — you don't need a physical USB token" ([Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)). |

The CSBR names no products; which cloud HSMs and which signing services qualify is a matter
for each CA's documentation and each service's FIPS/CC certificates. Microsoft states its own
compliance level as FIPS 140-3 Level 3 ([FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)),
comfortably above the §6.2.7.3 Signing Service floor.

Microsoft's own summary of the practical consequence, for what it is worth: "As of June 2023,
the CA/Browser Forum requires private keys for OV certificates to be stored on a hardware
security module (HSM) or hardware token. Most CAs provide a compatible USB token or cloud HSM
option." ([Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options))

The security point underlying `docs/adr/0002-code-signing-at-the-share.md` survives all of
this intact: under the post-2023 rules a publicly trusted code signing key **cannot legitimately
exist as an exportable `.pfx` in a GitHub Actions secret**. If CI signing is ever wanted, the
compliant options are a self-hosted runner with a token, a cloud HSM, or a signing service — not
a secret.

---

## 5. How reputation accrues, and what survives a new build

**Both per-file-hash and per-certificate.** Microsoft is unambiguous that two signals exist
(quoted in §1 above). What is far less clear is the exact key used for the certificate signal.

### What the documentation says

> **New version:** Signing files using a trusted certificate can allow certificate reputation
> to build, potentially avoiding warnings on new files signed by the same trusted certificate.
> Unsigned files must build reputation anew with every update.

— [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

> Reputation builds from both the file hash and, for signed files, the publisher's certificate,
> so signing releases with the same identity lets certificate reputation carry forward.
> Unsigned files must rebuild reputation for every new hash.

— [Distribution feature status](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/distribution-feature-status)

Note the hedging in the first quote — "can allow", "potentially avoiding". Microsoft does not
promise that an established certificate suppresses the warning on a new hash. It promises the
mechanism exists.

### Thresholds

There are none published.

> As downloads accumulate: SmartScreen reputation builds up automatically. The prompt will stop
> appearing once the file hash has sufficient download history. There is no exact threshold, but
> it can take several weeks and hundreds of clean installs from a wide audience.

— [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

**"Hundreds of clean installs from a wide audience" is the sentence that decides this question
for us.** A handful of staff on one network share is neither hundreds nor wide. No amount of
patience reaches that bar.

### What happens on certificate renewal

The documentation only warns obliquely: "**Use a consistent signing identity** — changing your
signing certificate affects the publisher trust signal" (same page).

The explicit answer comes from a Microsoft employee in Q&A, which is primary but not normative.
Answering a German software publisher whose reputation vanished after an OV renewal, Pauline
Mbabu (Microsoft Employee) wrote on 2026-04-17:

> SmartScreen reputation is entirely reputation and telemetry based rather than certificate
> validity or malware status, so when you renew an OV certificate with a new signing key the
> existing reputation does not carry over […] there is no manual whitelisting, no fast-track for
> small publishers, and no direct SmartScreen contact channel beyond the supported submission
> workflows.

— [Microsoft Q&A: How can a small software publisher build SmartScreen reputation?](https://learn.microsoft.com/en-gb/answers/questions/5857071/how-can-a-small-software-publisher-build-smartscre)

This is consistent with the documentation but goes further than it. Treat it as a strong
indication, not as a Microsoft commitment.

### What I could not verify

- **Whether the certificate signal keys on thumbprint, public key, or subject DN.** Microsoft
  does not document this anywhere I could find. The 2012 blog post says EV certificates carried
  "a unique identifier which makes it easier to maintain reputation across certificate renewals"
  — implying the default (non-EV) behaviour was *not* to survive renewal, and that identifier
  was the EV OID, removed from roots in August 2024 per the Trusted Root Program requirements.
  That is circumstantial, not proof.
- **Whether any publisher-facing portal or API exposes current reputation state.** I found no
  primary source documenting one. Absence of documentation is not proof of absence, but combined
  with the Microsoft employee statement above ("no direct SmartScreen contact channel beyond the
  supported submission workflows") it is a reasonable working assumption that none exists.
- **How reputation attaches for Artifact Signing's daily-rotating certificates.** See §3.

---

## 6. Does submitting to Microsoft for malware analysis help?

**There is a supported route. Microsoft's own pages disagree about whether it does anything for
reputation, and the prioritisation rules work against low-volume software.**

### Microsoft says yes (three pages)

> If you believe a warning or block was incorrectly shown for a file or application, or if you
> believe an undetected file is malware, [submit a file](https://www.microsoft.com/wdsi/filesubmission/)
> to Microsoft for review. […] When submitting a file for Microsoft Defender SmartScreen, make
> sure to select **Microsoft Defender SmartScreen** from the product menu.

— [Microsoft Defender SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) (`ms.date` 2026-04-23)

> If you continue to encounter SmartScreen prompts for your application, please consider
> submitting the signed file through [Microsoft Security Intelligence](https://www.microsoft.com/wdsi)
> for further review.

— [Artifact Signing FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq)

> Enterprise IT administrators may optionally submit files for review via the
> [Microsoft Security Intelligence portal](https://www.microsoft.com/en-us/wdsi/filesubmission).
> This can accelerate trust for internal or managed deployments.

— [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

### Microsoft says no (same page as the third quote)

> There is no need (or mechanism) to manually submit a file for SmartScreen reputation review for
> consumer endpoints. Reputation builds organically through download volume.

— [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

The two statements sit in the same article, separated by one sentence. The reconciliation that
fits all the evidence: **submission is a detection-dispute channel, not a reputation-granting
channel.** It can clear a wrongly-applied block or PUA classification; it does not manufacture
download history. The "enterprise IT administrators" carve-out for "internal or managed
deployments" is the one place Microsoft claims it can accelerate trust, and that is precisely our
scenario — so it is worth one attempt, with low expectations.

### The mechanics

- Submit at [microsoft.com/wdsi/filesubmission](https://www.microsoft.com/en-us/wdsi/filesubmission).
  Categories are Home customer, Enterprise customer, and Software developer.
- **Sign-in is required.** "No. If you're an enterprise customer, you need to sign in so that we
  can prioritize your submission appropriately." Email submission is not accepted.
- **Dispute route for developers:** "Submit the file in question as a software developer. Wait
  until your submission has a final determination. If you're not satisfied with our determination
  of the submission, use the developer contact form provided with the submission results to reach
  Microsoft."
- **Statuses:** Submitted → In progress → Closed, tracked at
  [the submission history page](https://www.microsoft.com/wdsi/submissionhistory).

All from [Submit files for analysis by Microsoft](https://learn.microsoft.com/en-us/defender-xdr/submission-guide).

### The catch, in Microsoft's own words

> Prevalent files with the potential to impact large numbers of computers are prioritized.
> Authenticated customers, especially enterprise customers with valid Software Assurance IDs
> (SAIDs), are given priority.

— same page

Low-prevalence software is deprioritised **by design**. The German publisher cited in §5 submitted
on 7 April 2026 and was still "Pending" three days later when they escalated to Q&A; Microsoft's
employee response noted that "Pending" states "can persist without status updates and do not imply
a problem." If you have an enterprise agreement with a Software Assurance ID, using it materially
improves your position in the queue — that is the single documented lever available.

---

## Where the sources disagree

| Topic | Source A | Source B | Assessment |
| --- | --- | --- | --- |
| Can you submit for SmartScreen review? | [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation): "no need (or mechanism)" for consumer endpoints | [SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) and [Artifact Signing FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq): yes, submit via WDSI | Both true for different things: dispute ≠ reputation. The same article also carves out enterprise/managed deployments. |
| Artifact Signing country list | [Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart): 12 countries/regions for orgs | [Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options): US, Canada, EU, UK only | Quickstart is newer and is the page the FAQ points to. Both include the EU. |
| Three-year organisation age | Archived 2024 quickstart: "verifiable tax history of three or more years"; still repeated everywhere online | Current quickstart (no such requirement) + Microsoft employee, 2026-08-17: "no minimum org age restrictions" | Requirement appears withdrawn. No published change note. Verify before budgeting. |
| EV code signing status in Trusted Root Program | [Learn page](https://learn.microsoft.com/en-us/security/trusted-root/program-requirements) §3.D.3: Feb/Aug 2024 removal — but the page is marked superseded | [Current GitHub requirements](https://github.com/TrustedRootProgram/Program-Requirements/blob/main/Requirements.md): clause absent, EV Code Signing still appears in EKU/audit tables | The clause is spent, not reversed. Corroborated by three current Learn pages describing the resulting behaviour. |
| EV and SmartScreen | [2012 archived blog](https://learn.microsoft.com/en-us/archive/blogs/ie/microsoft-smartscreen-extended-validation-ev-code-signing-certificates) and [2021 Q&A](https://learn.microsoft.com/en-us/answers/questions/417016/reputation-with-ov-certificates-and-are-ev-certifi): instant reputation | Three current Learn pages: removed in 2024 | Current docs win outright. The 2012 post remains online and unannotated, which is why the claim persists. |

---

## What this means for us

### Before spending anything, work out whether SmartScreen is even involved

Microsoft is explicit:

> SmartScreen protects against malicious files from the internet. It doesn't protect against
> malicious files on internal locations or network shares, such as shared folders with UNC paths
> or SMB/CIFS shares.

— [Microsoft Defender SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/)

And on the SmartScreen App Install Control policy: "This setting does not impact opening files
from USB devices, local network shares, or other non-internet sources."
([Available SmartScreen settings](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/available-settings))

We distribute from `X:\Apps\image-toolkit.exe`. By the documentation, that path should not be
subject to SmartScreen application-reputation checks at all. If staff are still seeing "Windows
protected your PC", the likely explanations are, in order:

1. **They downloaded from GitHub Releases in a browser.** That file carries Mark of the Web
   (Internet zone) and is subject to SmartScreen — and per the ADR, that asset is also unsigned.
   This is the most likely cause and costs nothing to fix.
2. **The share resolves to the Internet zone, not Local intranet.** Whether a source counts as
   trusted is decided by zone: "the policy determines a trusted source by checking its Internet
   zone. If the source comes from the local system, intranet, or trusted sites zone, then the
   download is considered trusted and safe"
   ([SmartScreenForTrustedDownloadsEnabled](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/smartscreenfortrusteddownloadsenabled)).
3. **It is not SmartScreen.** Smart App Control on Windows 11 blocks unsigned and unrecognised
   code independently, "supersede[s] SmartScreen Application Reputation", and its "signature checks
   apply to all executable files, not just those downloaded from the Internet"
   ([SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)).
   Or it is Defender flagging the PyInstaller bootloader, which is a different problem with a
   different fix (WDSI submission, §6).

**Do this first:** on a staff machine, check whether the EXE on the share carries a
`Zone.Identifier` alternate data stream and what zone it names, and read the exact wording of the
dialog people are seeing. Screenshot it. The answer changes which of the options below is even
relevant, and it costs nothing. *(This diagnostic is my inference from the zone documentation
above, not itself a Microsoft recommendation.)*

### Options that would not solve the problem, despite sounding like they would

- **Buying an EV certificate (~$400+/year).** The instant-bypass behaviour was removed in 2024.
  This is the single most common piece of stale advice on this topic and it is now explicitly
  disowned by Microsoft: "Paying a premium for EV solely to avoid SmartScreen warnings is no
  longer justified."
- **Buying an OV certificate (~$150–300/year).** Functionally identical to EV for SmartScreen.
  Adds a hardware token or cloud HSM obligation under CSBR §6.2.7.4.1 and buys nothing we do not
  already have from the enterprise key, unless that key is not publicly trusted (see below).
- **Azure Artifact Signing ($9.99/month) *as a SmartScreen fix*.** Microsoft states it "does **not**
  provide instant SmartScreen trust". It is an excellent answer to a *different* question — how to
  sign in CI without an exportable key — and a poor answer to this one.
- **Waiting for reputation to accrue.** "Several weeks and hundreds of clean installs from a wide
  audience." We have a handful of staff. This threshold is not reachable, ever, and every new build
  resets hash reputation anyway. Any recommendation premised on download volume is inapplicable to
  us and should be discarded on sight.
- **Submitting to WDSI expecting a reputation grant.** It is a detection-dispute channel, and
  prioritisation is explicitly by prevalence. Worth one attempt under the enterprise/managed-deployment
  carve-out, not worth planning around.
- **Publishing to the Microsoft Store.** It genuinely would work — Store MSIX packages are re-signed
  by Microsoft and "Users will never see a SmartScreen warning for a Store-installed app" — but it
  would mean repackaging an 80 MB PyInstaller one-file EXE as MSIX and listing an internal archival
  tool in a public catalogue. Not proportionate.

### Options that plausibly do work, cheapest first

1. **Keep the binary out of the Internet zone. (Cost: one IT ticket.)**
   Add the file server to the Local intranet zone by Group Policy so copies from the share do not
   acquire Mark of the Web, and make the ADR's existing position visible to staff: the share is the
   distribution channel, the GitHub asset is a build output. If the warning is MOTW-driven — which
   the documentation suggests it must be, since SmartScreen does not evaluate share-resident files —
   this is the entire fix.

2. **Confirm the enterprise certificate's root is trusted on every managed machine. (Cost: one IT
   ticket.)**
   Microsoft lists this as a supported pattern: "Enterprise internal distribution — your IT
   department can deploy the certificate as a trusted root via Intune or Group Policy, allowing
   managed devices to install the app silently"
   ([Code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)).
   If the enterprise key chains to an internal CA, this is what makes the signature mean anything on
   staff machines — and without it, SmartScreen treats the file exactly as if it were self-signed.
   Note the CSBR explicitly does not govern internal enterprise PKI (§1.1), so there are no hardware
   obligations attached to that key from the Forum's side.

3. **One WDSI submission as an enterprise customer. (Cost: free, plus an hour.)**
   The only documented path where Microsoft claims submission "can accelerate trust for internal or
   managed deployments". Sign in, pick "Enterprise customer", select **Microsoft Defender SmartScreen**
   as the product, and supply the Software Assurance ID if we have one — that is the one documented
   lever on queue priority. Expect no SLA and a possibly indefinite "Pending".

4. **Azure Artifact Signing, budgeted honestly. (Cost: $9.99/month ≈ $120/year, plus a paid Azure
   subscription and 1–20 business days of identity validation.)**
   Buy this if we want a *publicly trusted* signature — for the verified publisher name in any dialog
   that does appear, for Smart App Control compatibility on Windows 11 machines, or because a future
   auditor asks. It also resolves the CI tension in ADR 0002 properly: the private key is never
   exportable and is never given to us, so there is no key to leak into a GitHub secret. Germany is
   in the EU, so we are eligible on both of Microsoft's conflicting country lists, and the three-year
   organisation-age barrier appears to be gone. **Do not buy it expecting the warning to stop.**

5. **Do not move the enterprise key into CI.** Everything found here supports ADR 0002. Under CSBR
   §6.2.7.4.1 (effective June 2023) a publicly trusted signing key cannot legitimately live as an
   exportable file in a secret store at all; and for an internal key, the blast-radius argument in the
   ADR stands on its own. If manual signing starts getting missed, the ADR's own answer — a CI check
   that fails the release when the asset is unsigned — remains the right one, or Artifact Signing per
   option 4.

### The honest summary

At our volume, the reputation mechanism will never fire. No certificate purchase changes that, and
the two purchases people normally reach for (EV, then OV) are the two Microsoft has most clearly
disowned for this purpose. The tractable fixes are environmental — zone configuration, root trust on
managed machines, and not routing staff through a browser download — and they are free. The only
spend worth considering is $120/year for Artifact Signing, and it should be justified as *CI-safe
signing with a publicly trusted identity*, not as a SmartScreen fix, because Microsoft says in plain
words that it is not one.

---

## Sources

Normative / primary:

- [CA/Browser Forum — Code Signing Baseline Requirements v3.11.0 (16 June 2026)](https://cabforum.org/uploads/CA-Browser-Forum-CSCBR-3.11.0.pdf) · [working group page](https://cabforum.org/working-groups/code-signing/requirements/)
- [Microsoft Trusted Root Program — Program Requirements (Learn, superseded)](https://learn.microsoft.com/en-us/security/trusted-root/program-requirements) · [current source of truth on GitHub](https://github.com/TrustedRootProgram/Program-Requirements)
- [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
- [Code signing options for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
- [Current status of Windows app distribution features](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/distribution-feature-status)
- [Microsoft Defender SmartScreen overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/) · [available settings](https://learn.microsoft.com/en-us/windows/security/operating-system-security/virus-and-threat-protection/microsoft-defender-smartscreen/available-settings)
- [Smart App Control overview](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/overview)
- [What is Artifact Signing?](https://learn.microsoft.com/en-us/azure/artifact-signing/overview) · [Quickstart](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) · [FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq) · [Certificate management](https://learn.microsoft.com/en-us/azure/artifact-signing/concept-certificate-management) · [Pricing](https://azure.microsoft.com/en-us/pricing/details/artifact-signing/)
- [Submit files for analysis by Microsoft](https://learn.microsoft.com/en-us/defender-xdr/submission-guide) · [WDSI file submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission)
- [Microsoft Edge policy: SmartScreenForTrustedDownloadsEnabled](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/smartscreenfortrusteddownloadsenabled)
- Azure Retail Prices API, `https://prices.azure.com/api/retail/prices` (queried 2026-09-18)

Primary but non-normative (used only where labelled):

- [Microsoft SmartScreen & EV Code Signing Certificates (archived IE blog, 2012-08-14)](https://learn.microsoft.com/en-us/archive/blogs/ie/microsoft-smartscreen-extended-validation-ev-code-signing-certificates)
- [Microsoft Q&A: OV vs EV reputation (2021-06-07)](https://learn.microsoft.com/en-us/answers/questions/417016/reputation-with-ov-certificates-and-are-ev-certifi)
- [Microsoft Q&A: How can a small software publisher build SmartScreen reputation? (2026-04)](https://learn.microsoft.com/en-gb/answers/questions/5857071/how-can-a-small-software-publisher-build-smartscre)
- [Microsoft Q&A: Artifact Signing organisation age eligibility (2026-08-17)](https://learn.microsoft.com/en-us/answers/questions/5977141/azure-artifact-signing-trusted-signing-is-a-us-llc)
- [Microsoft Q&A: SmartScreen reputation reset following EV renewal (2026-05)](https://learn.microsoft.com/en-us/answers/questions/5900208/smartscreen-reputation-reset-following-ev-certific)
- [Microsoft Q&A: Artifact Signing, warnings from new intermediate CAs (2026-04-16)](https://learn.microsoft.com/en-us/answers/questions/5861538/azure-trusted-signing-still-seeing-smartscreen-war)
- [Wayback: Trusted Signing quickstart, 2024-07-26 snapshot](https://web.archive.org/web/20240726101000/https://learn.microsoft.com/en-us/azure/trusted-signing/quickstart)
- [Trusted Signing Public Preview Update (body not retrievable; see §3 caveat)](https://techcommunity.microsoft.com/blog/microsoft-security-blog/trusted-signing-public-preview-update/4399713)
