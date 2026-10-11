# Handwriting recognition for colonial-era English does not belong inside the EXE

Research note for `P3-W1-E1-016` through `P3-W1-E2-022`. Researched 2026-09-23.

Context this was written against: `image-toolkit.exe` is a PyInstaller one-file Windows
EXE of roughly 80 MB, run offline by a handful of staff from `X:\Apps\image-toolkit.exe`
(see `docs/adr/0001-single-web-ui-adapter.md` and `docs/adr/0002-code-signing-at-the-share.md`).
`requirements.txt` holds thirteen pinned dependencies, none of them a machine-learning
framework. The existing OCR path (`modules/ocr_pdf/core.py`) shells out to Tesseract per
page, optionally hands the document to OCRmyPDF for PDF/A, runs a quality gate
(`assess_ocr_readiness`) that withholds the OCR text layer from pages it judges too poor,
and assembles page PDFs with `merge_page_pdfs`. Input is microfilm-derived scans: low
contrast, grain, bleed-through, skew. Several of the mechanisms below only work with a
GPU, a Linux host, a network connection, or a locally transcribed training set, and that
is called out each time.

## How to read this

Every claim is traced to the document that owns it. Sources are ranked:

- **Primary, authoritative** — the project's own repository, its package metadata, the
  official documentation, the model card or Zenodo record for a specific model, the
  vendor's own pricing page.
- **Primary, measured** — peer-reviewed or preprint papers that report error rates they
  measured themselves, with the corpus described. Two are used heavily and both are
  named with their limitations.
- **Not used** — blog roundups, listicles, "best OCR tool" comparisons, and vendor
  marketing claims that are not attached to a number and a test set. Where a vendor
  marketing page is quoted it is labelled as such.

Error rates below are **CER** (character error rate) and **WER** (word error rate).
The field's own quality bands, as cited in Crosilla et al.: "a CER below 5% is considered
very good, if it falls in a range between 5 to 10% is good […] excellence is achieved
with a CER below 2.5%", and "the score below 90% of accuracy, meaning a CER above 10%
it's an indication of poor quality"
([arXiv:2503.15195](https://arxiv.org/abs/2503.15195), p. 28). Keep those bands in mind:
almost nothing below lands in the "very good" band on the kind of material we hold.

---

## The recommendation, up front

**Do not build an HTR engine into `image-toolkit.exe`.** Three independent reasons, each
sufficient on its own:

1. **The best-fitting open-source engine does not run on Windows.** Kraken — which owns
   the only pretrained model in existence trained specifically on 18th-century American
   manuscripts — declares `Operating System :: POSIX` in its PyPI metadata and its README
   says "Kraken can be run on Linux or Mac OS X (both x64 and ARM)". Windows is not
   mentioned, supported, or tested. See §1.
2. **Every remaining engine drags in a deep-learning runtime.** Kraken and TrOCR need
   PyTorch; the Windows CPU wheel for `torch` 2.14.0 is **124.1 MB compressed** before
   any model weights, which would roughly triple an 80 MB EXE. Calamari needs TensorFlow.
   See §6.
3. **The output would be a misleading text layer, which the codebase already has a gate
   to prevent.** The best measured result on 18th/19th-century English *including
   microfilm scans* is a strict CER of **7.3%** — about one wrong character in fourteen —
   and that was Claude Sonnet 3.5 over an API, not anything shippable offline. See §7.

**What to do instead**, cheapest first:

- **Gather the benchmark set first.** `P3-W1-E1-017` is still the right first move and
  is now the *only* move that should happen before anything else. §10 says what a good
  one looks like.
- **For actual production transcription, use Transkribus.** It is the incumbent, its
  English models are the only ones with published CER figures on this material, and at
  **€99/year** (Scholar, 900 credits, 1 credit = 1 handwritten page) it costs less than
  half a day of staff transcription time. §4.
- **If a toolkit feature is ever built, make it export a transcript sidecar, not a
  silent PDF text layer.** §8.
- **Revisit in mid-2026 if the Transkribus API and on-premise offering ship**, and
  revisit sooner if kraken's PP-OCRv6 line recognizers get an ONNX export. §9, §11.

---

## Comparison table

Judged against the four constraints in the brief. "Offline in EXE" means: can this run
inside a one-file PyInstaller Windows EXE with no network?

| Candidate | 1. Offline in a Windows EXE | 2. Microfilm-grade input | 3. Honest searchable-PDF output | 4. Licence & cost |
| --- | --- | --- | --- | --- |
| **Kraken** | ❌ **No.** PyPI classifier is `Operating System :: POSIX`; README says Linux/macOS only. Needs `torch>=2.9.0` (124 MB wheel) plus `lightning`, `scikit-learn`, `scipy`, `pyarrow`, `coremltools` | Trained largely on damaged historical material; RevCity model's corpus explicitly has "varying degrees of damage and noise" — but no published microfilm-specific figure | Own segmentation + recognition, outputs ALTO/PageXML/hOCR with per-line confidence, so a gated layer is constructible | Apache-2.0. Free. Models on Zenodo, mostly Apache-2.0 or CC-BY-4.0 |
| **Calamari** | ⚠️ `OS Independent` classifier, but needs `tensorflow>=2.4.0`. Last release **2.3.1, 2024-11-12** — 22 months stale | Unknown for handwriting: **no handwriting models exist** in `calamari_models` | Line-level only; **brings no segmentation** ("OCR Engine based on OCRopy and Kraken") | **GPL-3.0** — copyleft, a real question for a distributed EXE. Free |
| **TrOCR** | ⚠️ Possible but heavy. Needs PyTorch + `transformers`. `trocr-base-handwritten` weights alone are **1,333 MB**; large is **2,229 MB**; small is **246 MB** | Trained on IAM: **modern** English handwriting, clean, 20th-century. No historical or microfilm exposure | **Line-level only** — "single text-line images". Needs a separate segmenter you would have to supply | MIT (base-handwritten card). Free |
| **PaddleOCR** | ✅ `OS Independent`, no PyTorch | PP-OCRv5's own handwritten-**English** recognition metric is **0.5806** (server) / 0.4944 (mobile). Its handwriting story is Chinese-first | Detection + recognition in one stack; but at that accuracy the layer would be noise | Apache-2.0. Free |
| **Transkribus** | ❌ **Cloud only.** On-premise "coming soon"; API "Launching June 2026" | The incumbent on exactly this material; `B2022 English Model M4` reports **3.5% CER** on its own validation set. Independent tests put it at 7–10% CER on unseen material | Returns PageXML with confidences; you would build the PDF locally | **€99/yr** Scholar (900 credits); **€449/yr** Team (1,500); Free tier 50 credits/month; on-demand 250 credits **€59.50**. 1 credit = 1 handwritten page. Prices include 20% Austrian VAT |
| **eScriptorium** | ❌ Web application. "Linux and Mac or on WSL on Microsoft Windows"; GPU "indispensable" for segmentation training | Wraps kraken, so same material profile | Platform for correction, not a PDF producer | MIT. Free, but it is a server you operate |
| **Loghi** | ❌ Docker. "Loghi works best on Linux"; CPU-only "will be very slow" | Built by KNAW for Dutch national-archive scans | Pipeline outputs PageXML | MIT. Free, but it is a Docker stack |
| **Hosted VLM (Claude / GPT / Gemini)** | ❌ **Requires sending archival images to a third party.** Not offline | Best measured result on 18th/19th-c English incl. microfilm: **7.3% strict CER** | Good enough only for search, not for display as authoritative text | Per-token. Measured at **$0.0038–$0.0096 per page** vs Transkribus $0.26 |
| **Local open-weight VLM** | ❌ 7B–12B params ≫ EXE budget, and needs a GPU to be usable | Qwen2-VL-7B reached **8.01% CER** on Bentham (18th–19th-c English) — best open model tested, and better than GPT-4o | Same caveat as above | Apache-2.0 / varied. Free, but not shippable here |

---

## 1. Kraken — the right engine, on the wrong operating system

**Kraken is the strongest technical fit for this material and cannot be installed on
Windows.**

The README is explicit about platforms:

> Kraken can be run on Linux or Mac OS X (both x64 and ARM). Installation is through the
> on-board *pip* utility.

> kraken works both on Linux and Mac OS X and with any python interpreter between 3.10
> and 3.13.

— [github.com/mittagessen/kraken](https://github.com/mittagessen/kraken)

Windows is never mentioned. This is corroborated by the package's own metadata: kraken
7.1.1 (released 2026-09-04) declares exactly one operating-system classifier,
`Operating System :: POSIX`, and no `Microsoft :: Windows` classifier
([PyPI JSON API for `kraken`](https://pypi.org/pypi/kraken/json), queried 2026-09-23).

**Caveat, stated plainly:** a POSIX classifier and a README that omits Windows are
*declarations of support*, not proof that `pip install kraken` fails on Windows. I could
not test this — I have no Windows machine — and a pure-Python package with wheels for all
its dependencies might well import. But kraken depends on `coremltools~=9.0`, which is an
Apple toolchain, and on `pyvips` for the PDF extra, which needs a native libvips. Treat
"does not run on Windows" as the documented position and the safe planning assumption, and
treat "someone got it working" as an unverified claim until someone in this project runs
it. **This is the single highest-value thing to test if the question is ever reopened.**

### What kraken does

"fully trainable layout analysis, reading order, and character recognition", with output
in "ALTO, PageXML, abbyyXML, and hOCR, with word bounding boxes and character cuts", under
the Apache 2.0 licence ([kraken.re](https://kraken.re/main/index.html)). **Segmentation is
included** — this matters, see §5. Per-line confidences in the ALTO/PageXML output are what
a quality gate would key on.

### The model zoo — and the model that was made for us

Kraken's model repository is a Zenodo community. Queried on 2026-09-23 it holds **81
records** ([`zenodo.org/api/communities/ocr_models/records`](https://zenodo.org/communities/ocr_models)).
Two are directly relevant:

**The RevCity Model** — the find of this investigation.

> This is a text recognition model trained on the Revolutionary City dataset of
> handwritten Latin-script text in English […]. The material encompasses English text
> (~95k lines) in a variety of hands, with varying degrees of damage and noise. […] The
> model was trained from scratch using the python HTR package kraken […]. Work on this
> model was sponsored by the Center for Digital Scholarship at the American Philosophical
> Society.

— [The RevCity Model: HTR Recognition Model trained on 18th century English handwriting](https://doi.org/10.5281/zenodo.19238205),
published 2026-03-26, Apache-2.0, model file `revcity_july_2025.mlmodel` at **16.2 MB**.

Its bundled `metadata.json` (fetched from the Zenodo record) reports
`"accuracy": 93.43959093093872` and summarises itself as "a kraken recognition model for
HTR trained on a approximately 3000 page corpus of 18th century archival documents in
English". **That is roughly 6.6% CER** — in the field's "good", not "very good", band.

The underlying ground truth is
[The Revolutionary City Corpus (1758–1805)](https://doi.org/10.5281/zenodo.15776323)
(CC-BY-4.0, 2025-06-30), a partnership of the American Philosophical Society, the
Historical Society of Pennsylvania and the Library Company of Philadelphia covering
Philadelphia and the American Revolution: **3,316 pages, 95,990 lines, 2,997,053
characters**, "a wide variety of variation in hands, handwriting styles, paper quality and
levels of damage", majority 1774–1783. This is as close a match to colonial/early-American
material as a public dataset gets.

**Caveat:** the 93.44% figure is the model's self-reported training accuracy in its own
metadata, on its own corpus. It is not an independent evaluation, and it says nothing
about performance on *our* microfilm. Expect worse.

**PP-OCRv6 for kraken** — three line recognizers (tiny ~0.69M params / 2.8 MB, small
~3.24M, medium ~15.92M / 63.8 MB), Apache-2.0, published 2026-08-04, trained on 44
languages including a large English mixture that itself includes IAM and RevCity. The
medium model's published evaluation table gives **English: 5.90% CER, 20.35% WER** over
2,005 test lines
([medium](https://doi.org/10.5281/zenodo.21788410), [tiny](https://doi.org/10.5281/zenodo.21788403)).

Two honest caveats the authors state themselves:

> No attempt has been made to split in a manner that separates documents between train and
> test. The scores below are therefore best read as in-domain generalization.

> No attempt has been made to normalize the source datasets to a single set of
> transcription guidelines; the corpus mixes conventions, so inconsistent output is to be
> expected.

The size figures are the interesting part for us: **a 2.8 MB or even a 63.8 MB model is
entirely affordable in an 80 MB EXE.** The model was never the problem. The runtime is.

---

## 2. Calamari OCR — printed-text engine, no handwriting models, GPL

**The TODO describes Calamari as "respected in handwritten and historical OCR circles".
The first half of that is defensible for *printed* historical text; for handwriting it is
not supported by the project's own artefacts.**

- It is "an OCR Engine based on OCRopy and Kraken using Python 3", line-based, GPL-3.0
  ([github.com/Calamari-OCR/calamari](https://github.com/Calamari-OCR/calamari)).
- Its pretrained model repository lists nine models: `gt4histocr`, `antiqua_historical`
  (+`_ligs`), `fraktur_historical` (+`_ligs`), `fraktur_19th_century`, `uw3-modern-english`,
  `idiotikon`, `historical_french`
  ([Calamari-OCR/calamari_models](https://github.com/Calamari-OCR/calamari_models), MIT).
  **Every one is a printed-text model.** GT4HistOCR is a corpus of historical *printings*;
  Fraktur and Antiqua are typefaces. There is no handwriting model.
- It requires `tensorflow>=2.4.0` and `ocrd-fork-tfaip`; the most recent release on PyPI is
  **2.3.1, uploaded 2024-11-12** ([PyPI](https://pypi.org/pypi/calamari-ocr/json), queried
  2026-09-23). Twenty-two months without a release is not abandonment, but it is not the
  "active project" the TODO implies either.
- Licence is **GPL-3.0**, which is the only copyleft licence among the candidates and
  would need a considered answer before bundling into a distributed binary.
- It is line-recognition only. Segmentation is not in scope; you would pair it with
  OCRopy or kraken, which puts you back on §1's platform problem.

Using Calamari here would mean training a handwriting model from scratch, on a TensorFlow
stack, with no pretrained starting point. That is strictly worse than kraken, which has a
starting point.

---

## 3. TrOCR — modern English handwriting, line-level, gigabyte-scale weights

**TrOCR is a real handwriting model. It was trained on the wrong century of handwriting,
it only reads one line at a time, and its weights are larger than the entire EXE.**

From the model card for `microsoft/trocr-base-handwritten`:

> TrOCR model fine-tuned on the IAM dataset

> You can use the raw model for optical character recognition (OCR) on **single text-line
> images**.

— [huggingface.co/microsoft/trocr-base-handwritten](https://huggingface.co/microsoft/trocr-base-handwritten),
MIT licence, 0.3B params.

**IAM is modern English handwriting.** It is a corpus of contemporary writers copying
sentences from the Lancaster–Oslo/Bergen corpus onto forms, collected in the late 1990s.
Nothing in it is a colonial hand, a secretary hand, an 18th-century abbreviation, a long s,
or a microfilm scan. A model fine-tuned on IAM has no reason to read a 1776 letter well,
and the benchmark numbers in §7 confirm it does not.

Checkpoint sizes, from the Hugging Face API (queried 2026-09-23, `?blobs=true`):

| Checkpoint | Weights file | Size |
| --- | --- | --- |
| `microsoft/trocr-small-handwritten` | `pytorch_model.bin` | **245.9 MB** |
| `microsoft/trocr-base-handwritten` | `model.safetensors` | **1,333.4 MB** |
| `microsoft/trocr-large-handwritten` | `pytorch_model.bin` | **2,229.0 MB** |

Even the small checkpoint is three times the size budget that would be comfortable, and
that is before PyTorch. The `trocr-large-handwritten` and `trocr-small-handwritten` cards
do not declare a licence in their metadata; only `trocr-base-handwritten` declares MIT.
I could not verify the licence of the other checkpoints from a primary source.

**Line-level only is the bigger structural problem.** TrOCR takes a cropped line image and
returns a string. It has no layout analysis, no line detection, no reading order. To use it
on a page you must first segment that page into lines — which means a second component,
which for historical manuscripts realistically means kraken's segmenter (§1's platform
problem) or building a baseline detector yourself.

The TODO's "likely requires a custom page-to-text pipeline" is correct and, if anything,
understated.

---

## 4. Transkribus — the realistic answer, and exactly what it costs

**Transkribus is the incumbent for archival HTR, has the only published English models
with CER figures on early-modern hands, and is cloud-only today.**

### The public English models

**`B2022 English Model M4`**, created by the Beyond 2022 project at Trinity College Dublin:

| Property | Value |
| --- | --- |
| Date range | "Early 17th to late 19th century" |
| Words | 759,625 |
| Training pages | 2,934 |
| Lines | 102,881 |
| Hands represented | 40 |
| Reported CER | **"Very low error rate 3.5% CER"** (validation set) |
| Best on | "particularly effective on secretary and copperplate texts" |

— [transkribus.org/models/b2022-english-model](https://www.transkribus.org/models/b2022-english-model)

The same page carries the vendor's own hedge: "actual results may vary depending on
handwriting style, document condition, and material similarity to training data."

The Transkribus English landing page also names `Text Titan II` (a "Super Model"),
`Transkribus Print M1`, a `John Locke HTR Model` and an Irish–English bilingual model, and
explicitly claims coverage of "Colonial-era American documents and plantation records" and
"Early American land grants, deeds, and town records"
([transkribus.org/languages/english](https://www.transkribus.org/languages/english)).
**That page publishes no CER figures**, so treat the colonial-American claim as marketing
until measured against our own material.

Transkribus's own early-modern page claims "95–99% with matched model", immediately
qualified as "figures based on well-preserved documents with a matched HTR model"
([transkribus.org/early-modern-handwriting-recognition](https://www.transkribus.org/early-modern-handwriting-recognition)).
Microfilm-derived scans are not well-preserved documents in that sense. **Independent
measurements in §7 put Transkribus at 7–10% CER on unseen 18th/19th-century English**,
not 1–5%.

For English secretary hand specifically, Transkribus's own blog reports the Egerton model
achieving "a character error rate (CER) of just 3%" on **750,000 words** of training data,
while noting deposition hands "remain some of the most difficult in terms of readability"
with a target of only "better than a 7% CER for even the most difficult hands"
([Reading English Secretary Hand with AI: the Egerton Model](https://www.transkribus.org/blog/reading-english-secretary-hand-with-ai-the-egerton-model)).
Note what that says: 3% CER *cost three quarters of a million transcribed words*.

### The money, precisely

From [transkribus.org/pricing](https://www.transkribus.org/pricing) and
[transkribus.org/credits](https://www.transkribus.org/credits), read 2026-09-23. All prices
include 20% Austrian VAT.

| Plan | Price | Credits |
| --- | --- | --- |
| Free | €0 | "50 credits every month at no cost", "no credit card required" |
| Scholar | **€99/year** (€8.25/mo) | 900 credits/year |
| Team | **€449/year** (€37.42/mo) | 1,500 credits/year |
| Organisation | Custom quote | 15+ seats, 75,000+ credits/yr, API access with "50% off API Credits" |
| On-demand pack | **250 credits, €59.50** | no expiry |

Credit consumption, per page:

| Operation | Credits |
| --- | --- |
| Handwritten text + lines | **1 credit / page** |
| Printed text + lines | 0.5 credits / page |
| Lines recognition only | 0.25 credits / page |
| Tables recognition | 1 credit / page |
| Fields recognition | 1 credit / page |

So the effective cost of handwritten-page recognition is: **free** for the first 600
pages/year on the Free tier; **≈ €0.11/page** on Scholar; **€0.238/page** buying credits
on demand. For a small archival team this is inexpensive in absolute terms — Scholar's
900 pages/year for €99 is cheaper than one staff-day of manual transcription.

**The caveat that matters for an offline desktop tool:** there is currently no way to
call this from the EXE. The API is *not yet available*:

> Launching June 2026

> EU-hosted (Austria) · GDPR-compliant

> API credits cost 50% less than Transkribus UI credits. Pay-per-use billing is available
> upon request.

> On-premises deployment coming soon for full data sovereignty.

— [transkribus.org/text-recognition-api](https://www.transkribus.org/text-recognition-api)

The pricing page independently marks the API as "Coming soon" on the Scholar and Team
plans. **"Launching June 2026" is a date already in the past as of this note's research
date (2026-09-23), and I could not verify from any Transkribus page whether it actually
shipped.** The help centre has a "Legacy API" page, which suggests an older REST interface
exists, but I could not retrieve its terms. Someone should simply log into the account and
look. Likewise, on-premise deployment is "coming soon" with no date; if that ships it
changes the analysis materially, because an on-premise Transkribus is the one option that
is both accurate and offline.

---

## 5. Segmentation — who brings it and who does not

Historical manuscripts need layout analysis and baseline/line detection before
recognition. Uneven margins, marginalia, insertions, slanted lines and bleed-through make
this the harder half of the problem on microfilm.

| Candidate | Segmentation |
| --- | --- |
| **Kraken** | ✅ Built in — "fully trainable layout analysis, reading order, and character recognition". The Zenodo zoo also carries dedicated segmentation models (e.g. "General segmentation model for print and handwriting", several D-FINE and YOLO-Seg region models) |
| **Transkribus** | ✅ Built in; billed separately at 0.25 credits/page, or bundled at 1 credit/page with recognition |
| **PaddleOCR** | ✅ Built in (detection + recognition) |
| **Loghi** | ✅ Via Laypa, which "specializes in the segmentation of documents, identifying different regions like paragraphs, page numbers, and most importantly, baselines" |
| **eScriptorium** | ✅ Via kraken |
| **Calamari** | ❌ Line-level engine only. Needs OCRopy, kraken or equivalent |
| **TrOCR** | ❌ "single text-line images". Needs a separate segmenter |

The toolkit's existing deskew and auto-crop help but do not substitute: they normalise the
page, they do not find the lines. **Any route that picks TrOCR or Calamari has two
components to build and ship, not one.**

---

## 6. What a deep-learning runtime would actually cost the EXE

Measured from PyPI, 2026-09-23, for CPython 3.12 / `win_amd64`:

| Wheel | Compressed size |
| --- | --- |
| `torch-2.14.0-cp312-cp312-win_amd64.whl` | **124.1 MB** |
| `onnxruntime-1.30.0-cp312-cp312-win_amd64.whl` | **14.3 MB** |

PyInstaller does not ship the wheel; it ships the unpacked contents, compressed again into
the one-file archive. The unpacked `torch` tree is substantially larger than 124 MB — the
bulk is native libraries (`libtorch_cpu`, MKL/oneDNN kernels) that compress poorly and that
PyInstaller's analysis notoriously struggles to trace, in the same way `tifffile`'s lazy
`imagecodecs` resolution already required eight explicit `hiddenimports` entries in
`packaging/dpa-toolkit.spec`. **A realistic expectation is that adding PyTorch takes the
EXE from ~80 MB to somewhere in the 250–400 MB range**, with a new class of packaging
failure that only shows up in the frozen build.

*(That range is my estimate from the wheel sizes and the existing spec's behaviour, not a
measured figure. Nobody has built it. If the decision ever turns on this number, build a
throwaway spec with `torch` added and measure it — that is a half-day, and it would replace
an estimate with a fact.)*

`onnxruntime` at 14.3 MB is a different story entirely, and it is the one path that could
fit. Kraken's PP-OCRv6 tiny model is 2.8 MB and its medium is 63.8 MB; a `.safetensors`
CTC line recognizer of that shape is exactly the kind of model that exports to ONNX. **But
I found no evidence that kraken publishes ONNX exports or that anyone has reimplemented its
segmenter outside kraken.** Taking that path means writing your own baseline detector,
polygon extraction, and CTC decoder — a genuine engineering project, not an integration.

On **CPU-only speed**: none of the primary sources publish CPU-only throughput for these
models. Loghi says CPU-only "will be very slow" and eScriptorium says a GPU is
"indispensable" for segmentation training and "highly recommended" for recognition models
— but both statements are about *training*, and inference on a small CTC recognizer is a
different workload. **I cannot honestly tell you whether kraken-class inference is
acceptable on staff laptops, and neither can the documentation. It is unknowable without a
test.**

---

## 7. What accuracy is actually achievable — real numbers from real projects

Two studies measured this properly on English manuscript material. Both are preprints;
both describe their corpora; neither is vendor-funded.

### Humphries et al. 2024 — the study whose corpus matches ours

[*Unlocking the Archives: Large Language Models Achieve State-of-the-Art Performance on the
Transcription of Handwritten Historical Documents*](https://arxiv.org/abs/2411.03340),
Mark Humphries et al., Wilfrid Laurier University, arXiv:2411.03340v1, 2 November 2024.

**Why this one matters more than any other source here:** the test corpus is
50 pages, **33 different hands**, 18th/19th-century North American English (fur trade
records), and:

> 13 are scans from black and white microfilms, 26 are medium to high quality
> scans/photographs, and 11 are photographs taken with an iPhone or similar handheld
> device. All are 96 dpi with resolutions between 1742x2048 and 1222x2048. Six of the
> documents are somewhat blurry, while eight were shot in a darkly lit room, producing an
> image with poor contrast between the text and page.

That is our material, down to the microfilm and the poor contrast. The paper elsewhere
names "the prevalence of poorly scanned microfilm and microfiche records" as a standing
HTR challenge.

**Strict CER** (any difference in capitalisation, punctuation or spelling counts as an
error), Table 1:

| Model | Strict CER | Strict WER |
| --- | --- | --- |
| Transkribus (PyLaia) | **10.3%** | 27.0% |
| Transkribus (Titan Super Model) | **8.0%** | 19.7% |
| Claude Sonnet-3.5 | **7.3%** | 15.9% |
| Gemini-1.5 Pro-002 | **8.5%** | 18.8% |
| GPT-4o (06-08-2024) | **11.0%** | 23.0% |

The authors' own summary: "on the task of achieving a perfect transcription, the
Transkribus models correctly transcribed between 90 and 92% of the characters and 73 and
80% of the words". With a "modified" metric that forgives historical spelling and
capitalisation, the best out-of-the-box result improves to **5.7% CER / 8.9% WER**, and a
two-pass pipeline where an LLM corrects another model's transcript reaches **1.8% CER /
3.5% WER**.

Cost and speed, Table 5:

| Model | Cost per page | Seconds per page |
| --- | --- | --- |
| Transkribus (either model) | **$0.26** | 23.58 |
| Claude Sonnet-3.5 | $0.0096 | 0.71 |
| GPT-4o | $0.0052 | 0.57 |
| Gemini-1.5 Pro-002 | $0.0038 | 0.56 |

**Caveats.** (a) Only 50 pages and one language; the authors say so. (b) The ground truth
was produced by correcting a Transkribus transcript, which could bias toward Transkribus's
conventions. (c) The model versions are from 2024 and are all superseded. (d) The
$0.26/page Transkribus figure is the authors' own derivation, and does not match the
€0.11–€0.238/page that today's published Transkribus pricing implies (§4) — **the pricing
page is the better source for cost; use this table for the error rates and the latency.**

### Crosilla, Klic & Colavizza 2025 — the broader benchmark

[*Benchmarking Large Language Models for Handwritten Text Recognition*](https://arxiv.org/abs/2503.15195),
arXiv:2503.15195, submitted 19 March 2025, revised 23 June 2025.

The relevant test set is **Bentham: English, 18th–19th century**, 12 pages. Table VIII:

| Model | CER | WER | WER-BoW |
| --- | --- | --- | --- |
| Transkribus "The Text Titan I" | **7.07%** | 12.41% | 8.54% |
| Qwen2-VL-7B *(open weights)* | **8.01%** | 12.94% | 11.00% |
| GPT-4o-mini | 9.48% | 15.09% | 13.16% |
| Claude 3.5 Sonnet | 10.97% | 14.46% | 12.24% |
| MiniCPM-V 2.6 *(open weights)* | 11.76% | 17.24% | 13.91% |
| GPT-4o | 16.62% | 20.73% | 18.89% |
| Pixtral-12B *(open weights)* | 28.08% | 38.25% | 30.32% |
| Phi-3-mini-128k *(open weights)* | 32.03% | 41.85% | 38.73% |
| InternVL2-8B *(open weights)* | 76.81% | 95.92% | 81.67% |

For contrast, on **IAM** (modern English handwriting — the data TrOCR was trained on), the
same models reach 1.71%–2.30% CER. The authors: "A clear disparity emerges between the
recognition of modern and historical handwriting."

**Two things this table settles.** First, *century matters more than model quality*: the
same models that hit 1.7% CER on modern handwriting hit 7–17% on 18th-century English.
Second, **the best open-weight model (Qwen2-VL-7B, 8.01%) beat GPT-4o (16.62%)** on this
material and came within a point of Transkribus — which is genuinely surprising, and is
the strongest evidence that a locally-runnable option could eventually exist. It is a 7B
model needing a GPU; it is not shippable in this EXE today.

Caveat the authors flag themselves: the Bentham dataset "was used in the pre-training of
existing Transkribus PyLaia models", so Transkribus's 7.07% may be flattered.

### Converging estimate

Across both studies, on 18th–19th-century English manuscripts with no local training:
**expect 7–11% CER.** On microfilm specifically, expect the upper end or worse. In the
field's own bands, that is "good" bordering on "poor quality", and it is roughly **one
wrong character in every ten to fourteen**.

---

## 8. Is a searchable PDF text layer even the right output?

**No — not as the only output, and not silently.**

The brief asks this head-on and the evidence answers it clearly. At 7–11% CER:

- **For full-text search, it is genuinely useful.** Humphries et al. argue transcriptions
  above ~96% accuracy are "good enough for most day-to-day use cases such as full text
  keyword and semantic search". At 90–93% you are below that, but a word with one wrong
  character still often matches a fuzzy search, and WER-BoW (word presence ignoring order)
  runs meaningfully lower than WER — 8.54% for Transkribus on Bentham against 12.41% WER.
- **For display or citation, it is actively harmful.** A PDF text layer looks
  authoritative. A reader copying a sentence out of a searchable PDF has no way to know
  which of its characters the machine invented. This is precisely the judgment
  `assess_ocr_readiness` already encodes: a bad text layer is worse than none.

The codebase already has the right instinct and the right seam. Three concrete shapes,
in order of increasing honesty:

1. **A transcript sidecar.** Write `<group_name>.txt` (or `.xml` preserving line
   coordinates and confidences) alongside the PDF, and do not touch the PDF text layer at
   all. Zero risk of misleading anyone; fully greppable on disk. **This is the
   recommended output** if anything is ever built.
2. **A confidence-gated text layer.** Every engine considered here (kraken, Transkribus,
   PaddleOCR) emits per-line confidence. Embed only lines above a threshold, and record
   which were withheld — exactly what `ocr_document_to_pdf` already does with the quality
   precheck, and exactly what the existing "OCR Flagged Pages" re-run affordance
   (`P2-W3-E1-004`) already exposes in the UI. The machinery exists.
3. **An annotated layer** marking the document as machine-transcribed with an estimated
   error rate in the PDF metadata. Cheap, and it is the difference between a research aid
   and a false record.

What should **not** happen is HTR text flowing into `merge_page_pdfs` on the same path as
Tesseract output, with no marker distinguishing 2%-CER printed text from 10%-CER cursive.

On `P3-W1-E1-016` ("main OCR tool or a separate HCR panel"): the evidence says **separate**,
and the reason is this section rather than anything about code structure. Printed OCR and
handwriting HTR have error rates an order of magnitude apart, need different output
contracts, and warrant different warnings to the user. Folding them into one panel would
let a staff member pick "handwriting" from a dropdown and get back something that looks
exactly like the printed-OCR output they trust.

---

## 9. Vision-language models — fastest-moving, and the one to re-check

**State of play as of 2026-09-23.** All figures below are from models released in
2024–2025 and benchmarked in 2024–2025 papers. **This is the section most likely to be
wrong within six months, and it should be re-dated before being relied on.**

### API-hosted

The measured results are in §7: best-in-class frontier models land at **7.3% strict CER**
on microfilm-inclusive 18th/19th-century English, beating Transkribus's Titan model, at
roughly 1/50th the cost and 1/40th the latency. Used as a *corrector* over another
engine's output, the same study reached **1.8% CER / 3.5% WER** — near-human.

**The institutional implication is the blocker, and it is not a technical one.** Using a
hosted VLM means transmitting images of archival holdings to a third-party US cloud. For
this project that means:

- Anything under donor restriction, embargo, or third-party copyright cannot go.
- The toolkit is currently **fully offline** by design and by distribution channel (a
  network share, no GitHub contact even for updates). Adding an outbound API call would
  be the first time the EXE talks to the internet, and would need an API key distributed
  to staff — a new secret with a new leak surface, in a project whose ADR 0002 already
  declines to put a signing key in CI.
- Humphries et al. note their own position: "all the documents we used in our testing
  dataset were out of copyright and in the public domain. The terms of service for the
  APIs we used in our testing also precludes OpenAI, Anthropic, and Google from retaining
  or using this data to train their models in future." Terms of service change; the
  institution's obligations to its depositors do not. **Verify current terms directly
  against the provider's enterprise agreement before any archival image leaves the
  building — do not rely on this note, or on a 2024 paper, for that.**
- One concrete failure mode from that paper worth knowing: Gemini-1.5-Pro-002 occasionally
  **hallucinated a citation**, attributing a document to a website that did not contain
  it, "roughly 1 in 30 times". VLMs do not merely misread; they confabulate plausible
  text. A CTC recognizer that misreads a word produces gibberish you can see. A VLM
  produces fluent, wrong English. **For an archival text layer that difference is
  serious**, and it argues for CTC engines over generative ones independent of CER.

Kraken's own PP-OCRv6 model card makes exactly this argument: the model "should offer
similar accuracy and generalization to VLM-based recognizers **without hallucinations**
and with vastly higher throughput"
([Zenodo](https://doi.org/10.5281/zenodo.21788410)). That is a partisan source — it is the
kraken maintainer describing a kraken model — but the mechanism is real and independently
evidenced by the Gemini finding above.

### Locally-runnable open weights

The Crosilla benchmark is the best primary evidence: **Qwen2-VL-7B reached 8.01% CER on
Bentham**, best of the open models and ahead of GPT-4o. MiniCPM-V 2.6 reached 11.76%.
Pixtral-12B, Phi-3-mini and InternVL2-8B were unusable (28%, 32%, 77%).

For this project that is an interesting result and a dead end: a 7B model is several GB of
weights and needs a GPU for tolerable latency. It cannot go in an 80 MB EXE, and the
target machines are staff desktops.

**What would change the answer:** a small (≤1B) open-weight model with published CER under
10% on historical English, distributed as ONNX. Nothing like that exists in the primary
sources I checked as of 2026-09-23. Kraken's `Party` full-page recognizer (Swin encoder +
a 40M-param Llama decoder, Apache-2.0,
[Zenodo](https://doi.org/10.5281/zenodo.20642057)) is the closest thing in the right
size class, but its card says it "is intended to be fine-tuned on some target dataset",
publishes no English CER figure, and it runs inside kraken (§1).

---

## 10. Is training avoidable, and what would it cost?

**Partly. A pretrained early-American model now exists — RevCity — which did not when the
TODO was written. It is probably not good enough alone on microfilm, and closing the gap
means transcribing ground truth locally.**

### Published guidance on how much ground truth

Transkribus's own figures:

> you will need at least **10,000 words of transcribed handwritten text** or 5,000 words of
> transcribed printed text to train **your first model**.

— [What is Ground Truth?](https://www.transkribus.org/blog/what-is-ground-truth)

Transkribus's help centre and training blog give the fuller range — roughly 5,000–15,000
words (about 25–75 pages) to start, a minimum of ~10,000 words *per hand* for variable
handwriting, and models above 100,000 words beginning to generalise to unseen hands. **I
could not retrieve the exact wording of those wider figures from the help-centre page
directly** (the page I fetched at
[help.transkribus.org/training-text-recognition-models](https://help.transkribus.org/training-text-recognition-models)
does not carry them), so treat the 10,000-word minimum as the verified number and the rest
as indicative.

What the real projects actually spent is more instructive than the minimum:

| Project | Ground truth | Result |
| --- | --- | --- |
| Transkribus Egerton (English secretary hand) | 750,000 words | 3% CER |
| B2022 English Model M4 | 759,625 words / 2,934 pages / 40 hands | 3.5% CER |
| RevCity (kraken, 18th-c American) | 3,316 pages / 95,990 lines / ~3.0M characters | ~6.6% (self-reported) |
| Cited in Humphries et al. | "manually transcribe 69,457 words (558 manuscript pages)" | 4.39% CER |

That last figure is the most useful yardstick for us, because it is the smallest: **~558
pages transcribed to reach 4.39% CER.**

### What that costs in staff time

Humphries et al. observe that "student RAs usually transcribe around 5-7 pages per day".
At that rate:

| Target | Pages of ground truth | Staff-days | Staff-weeks |
| --- | --- | --- | --- |
| Transkribus minimum first model (~10,000 words) | ~40–50 | **7–10** | 1.5–2 |
| The 4.39% CER result cited above | 558 | **80–112** | **16–22** |

Transkribus notes that correcting a machine transcript is "3–5x faster than transcribing
from scratch", which would cut those figures substantially — start from a RevCity or Text
Titan pass and correct it. Even so: **a serious local model is a multi-month commitment of
someone's time, not a sprint item.** That is the honest cost, and it is the number that
should decide `P3-W1-E1-016`.

### The realistic answer

- **Fully avoidable?** No. Nothing off the shelf will hit "very good" (<5% CER) on
  microfilm-derived colonial cursive. Every project that got there transcribed hundreds of
  pages first.
- **Partly avoidable?** Yes, and this is new since the TODO was written. RevCity (kraken,
  Apache-2.0, free) and Transkribus's B2022/Text Titan are real starting points for
  early-American English. A first pass from one of those, corrected by staff, is both a
  usable transcript *and* the ground truth for a fine-tune. That is the pattern every
  successful project in this note used.
- **The gating question is not "which engine" but "is a 90–93%-accurate transcript worth
  having?"** For search and discovery, probably yes. For publication, no. That is a
  curatorial decision, not an engineering one, and it should be made before any code.

---

## What is not knowable from here

Stated plainly, because the brief asks:

- **Whether kraken installs on Windows at all.** Documented as unsupported (§1). Untested
  by me — I have no Windows machine. This is the single test that could reopen the whole
  question.
- **CPU-only inference speed** for kraken, TrOCR or any of these on staff hardware.
  No primary source publishes it; it needs a measurement (§6).
- **The real EXE size increase** from bundling PyTorch. My 250–400 MB figure is an
  estimate from wheel sizes, not a build (§6).
- **How any of these perform on *our* microfilm.** Every number in §7 is from someone
  else's corpus. Bentham is clean manuscript imagery; the Humphries corpus is the closest
  match and it is 50 pages.
- **Whether the Transkribus API actually launched.** Its page says "Launching June 2026",
  now three months past. Log into the account and look (§4).
- **Current provider terms for archival images** sent to hosted VLMs (§9).
- **Licences for `trocr-large-handwritten` and `trocr-small-handwritten`** — not declared
  in their model card metadata (§3).

---

## The next concrete step

**`P3-W1-E1-017` — gather the benchmark set — is still the right first move, and it should
now be the *only* work done before a go/no-go.** Everything above is someone else's
corpus; this project's decision turns on numbers from this project's material.

A good benchmark set, based on what the studies above got right:

- **30–50 pages.** Humphries et al. used 50 and called it small; below 30 the variance
  swamps the signal.
- **Deliberately spanning difficulty**, in roughly the proportions of the real holdings:
  clean high-contrast microfilm, poor low-contrast microfilm, bleed-through, skew that
  survives the existing deskew pass, and at least a few pages of mixed print + handwriting
  (forms with handwritten entries), which is a distinct and harder case.
- **Many hands, not many pages of one hand.** 33 hands across 50 pages is the right shape.
  A model that reads one clerk well tells you nothing.
- **A diplomatic ground-truth transcription of every page**, made by staff, with a
  written convention for abbreviations, superscripts, long s, strikethroughs and
  marginalia decided *before* transcription starts. Every project in §10 named this as
  the thing that bit them. Without a fixed convention, CER measures your inconsistency
  rather than the model's.
- **Pages that have never been published online**, so no candidate model has seen them.
  Humphries et al. deliberately withheld their corpus for this reason.
- Kept in the repo or on the share as a fixed, versioned set, so every future engine is
  scored on the same pages.

That set costs roughly **1–2 staff-weeks** (§10's rate) and it is reusable forever. With
it in hand, the go/no-go is a day's work: run the pages through the Transkribus free tier
(50 credits/month covers 50 pages, at zero cost and with no install) against `B2022
English Model M4` and `Text Titan II`, score the CER, and compare against the 7–11%
expectation. If Transkribus cannot clear the bar on our material, no offline engine will,
and `P3-W1-E2-018` through `-022` can be closed as answered rather than tested one by one.

---

## Corrections to the TODO.md HCR section

Not applied — this note does not modify `TODO.md`. These are the claims the primary
sources contradict.

| Item | Current claim | Correction |
| --- | --- | --- |
| `P3-W1-E2-020` Kraken | "steeper workflow; less turnkey for desktop staff use" | **Understated to the point of being wrong.** Kraken's README states Linux/macOS only and its PyPI metadata declares `Operating System :: POSIX`. It is not "less turnkey" on Windows — it is undocumented and unsupported there. Also add: kraken now has the single best-fitting model available anywhere for this material (RevCity, 18th-c American English, Apache-2.0, 16.2 MB), which is the reason it is worth testing despite the platform problem. |
| `P3-W1-E2-021` Calamari | "respected in handwritten and historical OCR circles"; "good candidate if line-level workflows become acceptable" | **Wrong on handwriting.** All nine models in `calamari_models` are printed-text models (GT4HistOCR, Fraktur, Antiqua, UW3). There is no handwriting model to start from. Also add: GPL-3.0 (the only copyleft candidate), requires TensorFlow, last PyPI release 2.3.1 on 2024-11-12. |
| `P3-W1-E2-019` PaddleOCR | "support for printed text and handwriting scenarios"; "may handle mixed page conditions better than Tesseract" | **Overstated for English.** PaddleOCR's own PP-OCRv5 page reports handwritten-English recognition of **0.5806** (server) / 0.4944 (mobile). Its handwriting work is Chinese-first. No historical-manuscript models. Correct in its favour: it needs no PyTorch and is `OS Independent`, so the "heavier install" con is the wrong con — accuracy is. |
| `P3-W1-E2-018` TrOCR | "strongest open-source-looking starting point for English handwriting" | **Correct as written, and that is the problem** — "looking" is doing the work. It is trained on IAM, which is *modern* English handwriting, and it is line-level only. Add the hard numbers: base checkpoint weights are 1,333 MB, large 2,229 MB, small 246 MB, before PyTorch's 124 MB Windows wheel. |
| `P3-W1-E2-022` Comparison criteria | Five criteria listed | Add two the sources show are decisive: **(a) does the candidate bring its own segmentation** (TrOCR and Calamari do not); **(b) does it emit per-line confidence** (needed to extend the existing quality gate). |
| Section scope | Names four engines | **Transkribus is missing and is the likeliest realistic answer.** So are eScriptorium and Loghi (both viable, both server/Docker shaped), and hosted/local VLMs, which now match or beat dedicated HTR on 18th–19th-century English. |
| `P3-W1-E1-016` | Framed as an open question | The evidence answers it: **separate**, because the output contract differs (see §8), not for code-structure reasons. |
| `P3-W1-E1-017` | "Gather a benchmark set […] before choosing an engine" | **Unchanged and reinforced** — this should be the only item worked until it is done. |

---

## Sources

Engine and model primary sources:

- [kraken documentation](https://kraken.re/main/index.html) · [github.com/mittagessen/kraken](https://github.com/mittagessen/kraken) · [PyPI metadata for `kraken` 7.1.1](https://pypi.org/pypi/kraken/json) (queried 2026-09-23)
- [kraken model repository (Zenodo `ocr_models` community, 81 records)](https://zenodo.org/communities/ocr_models) · [The RevCity Model](https://doi.org/10.5281/zenodo.19238205) · [The Revolutionary City Corpus (1758–1805)](https://doi.org/10.5281/zenodo.15776323) · [PP-OCRv6 medium for kraken](https://doi.org/10.5281/zenodo.21788410) · [PP-OCRv6 tiny](https://doi.org/10.5281/zenodo.21788403) · [Party base model](https://doi.org/10.5281/zenodo.20642057) · [McCATMuS](https://doi.org/10.5281/zenodo.13788177)
- [github.com/Calamari-OCR/calamari](https://github.com/Calamari-OCR/calamari) · [Calamari-OCR/calamari_models](https://github.com/Calamari-OCR/calamari_models) · [PyPI metadata for `calamari-ocr`](https://pypi.org/pypi/calamari-ocr/json)
- [microsoft/trocr-base-handwritten](https://huggingface.co/microsoft/trocr-base-handwritten) · [microsoft/trocr-large-handwritten](https://huggingface.co/microsoft/trocr-large-handwritten) · Hugging Face model API (`?blobs=true`, queried 2026-09-23)
- [PaddleOCR documentation](https://www.paddleocr.ai/latest/en/index.html) · [PP-OCRv5 algorithm page](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html) · [PyPI metadata for `paddleocr`](https://pypi.org/pypi/paddleocr/json)
- [eScriptorium documentation](https://scripta.gitlab.io/escriptorium/) · [gitlab.com/scripta/escriptorium](https://gitlab.com/scripta/escriptorium)
- [github.com/knaw-huc/loghi](https://github.com/knaw-huc/loghi) (MIT, per the GitHub licence API)
- PyPI wheel sizes for `torch` 2.14.0 and `onnxruntime` 1.30.0, `cp312-win_amd64` (queried 2026-09-23)

Transkribus (vendor primary — pricing and model figures are the vendor's own):

- [Pricing](https://www.transkribus.org/pricing) · [Understanding Transkribus credits](https://www.transkribus.org/credits) · [Credit packages](https://www.transkribus.org/credit-packages) · [Text Recognition API](https://www.transkribus.org/text-recognition-api)
- [B2022 English Model M4](https://www.transkribus.org/models/b2022-english-model) · [English language page](https://www.transkribus.org/languages/english) · [Early modern handwriting recognition](https://www.transkribus.org/early-modern-handwriting-recognition)
- [Reading English Secretary Hand with AI: the Egerton Model](https://www.transkribus.org/blog/reading-english-secretary-hand-with-ai-the-egerton-model) · [What is Ground Truth?](https://www.transkribus.org/blog/what-is-ground-truth) · [Training Text Recognition Models (help centre)](https://help.transkribus.org/training-text-recognition-models)

Measured benchmarks:

- Mark Humphries, Lianne C. Leddy, Quinn Downton, Meredith Legace, John McConnell, Isabella Murray, Elizabeth Spence (Wilfrid Laurier University), [*Unlocking the Archives: Large Language Models Achieve State-of-the-Art Performance on the Transcription of Handwritten Historical Documents*](https://arxiv.org/abs/2411.03340), arXiv:2411.03340v1, 2 November 2024
- Giorgia Crosilla, Lukas Klic, Giovanni Colavizza, [*Benchmarking Large Language Models for Handwritten Text Recognition*](https://arxiv.org/abs/2503.15195), arXiv:2503.15195, 19 March 2025 (rev. 23 June 2025)
