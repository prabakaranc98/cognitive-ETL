# Cognitive ETL Blueprint

**Extract, Transform, Load — as a Cognitive Function.**

A low-friction system for turning books, papers, thoughts, conversations, and half-formed ideas into:

- reusable units of thinking
- linked knowledge
- small public artifacts
- a clean presentation layer you do not hate maintaining

This is not just ETL for data.
It is ETL for cognition:

- `Extract` = notice, capture, pull signal from the world
- `Transform` = clarify, compress, link, challenge, structure
- `Load` = publish, present, resurface, reuse

The key idea is simple:
**human + machine do the meaning work together; automation handles the boring load/presentation layer.**

---

## What This System Should Feel Like

If it creates friction, you will stop using it.
So the system should feel like:

- quick to add to
- easy to trust
- easy to review
- easy to ship from
- hard to lose context in

It should not feel like:

- a productivity tax
- a metadata prison
- a perfect taxonomy project
- a second job after reading

The system wins if it keeps you reading, thinking, and shipping.

---

## Core Thesis

Most knowledge systems fail because they over-reward input.

They track:

- books read
- highlights collected
- notes stored

But they do not create pressure to:

- think
- connect
- reuse
- publish

This system should reward:

1. extracting what matters
2. transforming it into clear atoms
3. loading it into useful public and private views
4. reusing old atoms in new artifacts

That is what makes it compound instead of accumulate.

---

## The Cognitive ETL Model

### 1. Extract

Raw material enters the system from:

- books
- papers
- articles
- podcasts
- conversations
- lectures
- slide decks
- fleeting thoughts

The output of extraction is not polish.
It is a **capture packet**.

A capture packet can contain:

- source title
- chapter or section
- raw highlights
- short notes
- one or two reactions
- screenshots or slide links
- a question worth keeping

Rule:
**capture fast, without demanding full structure.**

### 2. Transform

This is the real cognitive work.

The raw packet becomes:

- a `Source`
- a set of `Atoms`
- possible `Links`
- maybe one `Artifact` draft

Transformation is where AI helps most:

- drafting atomic claims
- suggesting links to existing ideas
- pulling out mechanisms and boundaries
- identifying contradictions
- creating first-pass summaries
- turning notes into artifact outlines

But the human should still own:

- what is actually true
- what is worth keeping
- what is too vague
- what should ship

Rule:
**AI proposes. Human approves.**

### 3. Load

Load does not mean "store somewhere."
It means "make it usable in multiple views."

The transformed knowledge should load into:

- a graph view
- a source view
- an artifact gallery
- a search index
- a recommendations layer
- a public storefront

Automation should dominate this step.

Rule:
**once an atom or artifact is approved, presentation should mostly build itself.**

---

## Human, AI, and Automation Roles

### Human

- chooses what to read
- decides what feels important
- approves atoms
- corrects weak claims
- ships artifacts
- builds taste over time

### AI

- cleans raw notes
- drafts structured atoms
- proposes links and tags
- spots duplicates
- turns atoms into summaries, posts, slides, or outlines
- helps maintain consistency

### Automation

- syncs local content
- builds JSON/indexes/graph data
- generates static pages
- deploys to GitHub Pages
- updates search and related-content views

This separation matters:

- human = judgment
- AI = synthesis
- automation = reliability

---

## Core Objects in the System

Keep the model small.
Too many object types will create friction.

### Source

A source is any input unit you learned from.

Examples:

- a book
- a paper
- an article
- a lecture
- a conversation

Minimal fields:

- `title`
- `type`
- `author_or_origin`
- `status`
- `domain`
- `source_link`
- `notes_link`
- `slides_link`

### Capture Packet

This is the raw intake object.
It is temporary and messy by design.

Minimal fields:

- `source_ref`
- `section`
- `raw_notes`
- `highlights`
- `questions`
- `session_date`

### Atom

This is the core unit of thought.
The graph should be built from atoms, not books.

Minimal fields:

- `claim`
- `definition`
- `because`
- `boundaries`
- `source_quote`
- `source_ref`
- `related_atoms`
- `confidence`
- `reuse_count`

### Artifact

An artifact is a consumable output created from one or more atoms.

Examples:

- a 5-slide deck
- a one-pager
- a blog post
- a short note
- a visual explainer

Minimal fields:

- `title`
- `format`
- `built_from_atoms`
- `summary`
- `artifact_link`
- `status`

---

## The System Architecture

```text
Inputs
  books / papers / articles / thoughts / conversations
        |
        v
Capture Layer
  quick notes, highlights, screenshots, voice-to-text, slide links
        |
        v
Transform Layer
  human + AI draft sources, atoms, links, artifact candidates
        |
        v
Knowledge Layer
  structured records for Sources, Atoms, Artifacts, Links
        |
        +--------------------+
        |                    |
        v                    v
Private Working Views    Public Presentation Views
  source dashboard         artifact gallery
  atom editor              graph explorer
  review queues            search / recommendations
  reuse tracking           GitHub Pages storefront
```

---

## Recommended Operating Surface

For low friction, the operating surface should be:

- `VS Code` for editing and review
- `Claude Code` for drafting and structuring
- `GitHub` for version history and deployment
- `GitHub Pages` for the public storefront

Optional adapters:

- `Notion` for relational editing and easy capture
- `Google Drive` for slides/docs
- `Obsidian` or local markdown folders for raw notes

Recommended principle:
**GitHub should be the durable build/deploy layer.**
Other tools can be inputs or convenience layers.

---

## Suggested Repo Shape

This is a good future shape for the repo if you want to grow it cleanly:

```text
cognitive-etl/
├── content/
│   ├── inbox/               raw capture packets
│   ├── sources/             cleaned source records
│   ├── atoms/               approved atomic notes
│   ├── artifacts/           artifact metadata
│   └── links/               optional explicit graph edges
├── scripts/
│   ├── ingest/              import from Notion, docs, markdown, web
│   ├── transform/           atom drafting, linking, dedupe, scoring
│   └── build/               search index, graph data, static pages
├── prompts/
│   ├── extract.md
│   ├── transform.md
│   └── artifact.md
├── src/
│   ├── cognitive_etl/
│   ├── templates/
│   └── static/
├── dist/
└── .github/workflows/
```

This gives you one clear place to:

- drop raw material
- review transformed knowledge
- ship outputs
- rebuild the site

---

## Low-Friction Rules

These rules matter more than tooling.

### Rule 1: No mandatory metadata at capture time

At capture time, only require enough to not lose the note.

Good:

- title
- source
- raw text

Bad:

- full tagging
- novelty scoring
- confidence scoring
- category perfection

Metadata should be suggested during transform, not forced during capture.

### Rule 2: Smallest useful unit

The unit of work should be:

- one chapter
- one paper section
- one article
- one conversation
- one idea burst

Not:

- one entire book
- one entire research area

### Rule 3: Reuse beats collection

The system should visibly reward:

- linking an old atom to a new source
- building a new artifact from old atoms
- revisiting and upgrading an old claim

### Rule 4: Shipping can be small

A valid artifact can be:

- 5 slides
- 1 page
- 1 note
- 1 visual
- 1 thread draft

You do not need a masterpiece to complete the loop.

### Rule 5: Every atom needs provenance

Every strong atom should point back to:

- a source
- a quote
- a context

Otherwise the graph becomes vibes instead of knowledge.

---

## What You Should Be Able to Add Easily

The system should make these additions trivial:

### Add a source

Example:
"I started reading `Thinking in Systems`."

The system should let you add:

- title
- author
- type
- current status

without making you fill ten extra fields.

### Add raw notes

Example:

- pasted highlights
- short bullets
- screenshots
- slide link

The system should accept ugly input.

### Add atoms

The system should let AI draft:

- claim
- definition
- because
- boundaries
- provenance

and let you approve or edit.

### Add artifacts

The system should let you attach:

- slide deck URL
- note URL
- post URL
- PDF URL

and connect that artifact to its underlying atoms.

This is important:
**slides and short notes should not live outside the graph.**
They should be linked as outputs of the same thinking pipeline.

---

## The Practical Workflow

### Workflow A: Reading Session

1. Read for 20 to 45 minutes.
2. Drop raw notes into the system.
3. Write:
   - what surprised me
   - what I disagree with
   - what changed for me
4. Ask AI to draft atoms from that session.
5. Approve only the good ones.

### Workflow B: Artifact Creation

1. Select 3 to 7 atoms.
2. Ask AI for:
   - a slide outline
   - a note
   - a one-pager
3. Edit lightly.
4. attach the final link
5. rebuild the storefront

### Workflow C: Weekly Review

1. Check which atoms were reused.
2. Merge duplicates.
3. strengthen weak definitions.
4. ship one small artifact.

This keeps the system alive without turning it into admin.

---

## What the Storefront Should Show

The public layer should be clean and legible.
Not everything needs to be public, but what is public should be consumable.

Core views:

- `Artifact Gallery`
- `Knowledge Graph`
- `Atom Explorer`
- `Source Index`
- `Search`

Nice additions later:

- related atoms
- "built from" sections on artifact pages
- domain clusters
- reading timeline
- recommendation trails

The storefront should answer:

- what are you thinking about?
- what have you shipped?
- what ideas connect across sources?

---

## Recommended Maturity Path

Do not think of this as a rigid timeline.
Think of it as a maturity ladder.

### Level 1: Capture + Manual Transform

- add sources
- add raw notes
- draft atoms manually or with light AI help
- build simple gallery/search pages

### Level 2: AI-Assisted Structuring

- auto-draft atoms from notes
- suggest related atoms
- draft artifact outlines
- generate source summaries

### Level 3: Connected Knowledge System

- explicit graph edges
- reuse tracking
- recommendations
- related artifacts
- stronger source-to-atom provenance

### Level 4: Seamless Publishing

- one-command build
- automatic deploy
- automatic graph/search refresh
- stable GitHub Pages storefront

---

## A Good Default Principle

If you are unsure where a feature belongs:

- if it helps you capture signal, it is `Extract`
- if it helps you clarify meaning, it is `Transform`
- if it helps others consume or helps you resurface later, it is `Load`

That framing keeps the architecture clean.

---

## What Success Looks Like

Success is not:

- having the most notes
- having the biggest graph
- having the most metadata

Success is:

- you keep using it
- reading becomes more mindful
- ideas get reused
- artifacts keep shipping
- old knowledge becomes easier to retrieve
- the public layer becomes a true reflection of your thinking

---

## Final Operating Statement

This system should behave like a **cognitive refinery**:

- the world provides raw material
- you and AI extract signal
- you and AI transform it into clean thought
- automation loads it into durable, searchable, shareable form

The end state is not just a second brain.
It is a **compounding thought infrastructure** that is:

- private when it needs to be
- structured where it matters
- public where it is useful
- simple enough that you do not leave it

---

## Short Version

Build a system where:

- capture is ugly but easy
- transformation is assisted but reviewed
- loading is automated
- reuse is rewarded
- shipping is small and frequent
- GitHub is the reliable surface
- the storefront is the clean output of the whole loop

That is Cognitive ETL.
