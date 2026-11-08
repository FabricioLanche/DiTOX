---
name: khipu-hpc-docs
description: Reference and how-to guide for Khipu, the HPC (Slurm) cluster of UTEC's COMPSUST center. Use when the user asks about accessing Khipu (SSH, keys, password), transferring files, submitting/monitoring/canceling Slurm jobs, partitions and nodes, available software/modules, Open OnDemand, VS Code Remote / Jupyter / Apptainer / PyTorch checkpointing on Khipu, or Khipu's usage policies and support. Content scraped from https://docs.khipu.utec.edu.pe/ (accessed 2026-09-21).
---

# Khipu HPC Docs

Khipu is the HPC (High Performance Computing) cluster of UTEC's Centro de
Investigación para la Computación Sostenible (COMPSUST). It uses **Slurm** as
its job scheduler. This skill packages the site content from
`https://docs.khipu.utec.edu.pe/` as offline reference material so an agent
can answer Khipu questions or help write Slurm scripts / SSH configs without
re-fetching the site every time.

The site is entirely in **Spanish** — keep answers in Spanish unless the user
writes in another language.

## When to use this skill

- Access: requesting an account, SSH login, changing password, SSH keys.
- File transfer: `scp` / `rsync` to/from Khipu.
- Running work: writing `sbatch` scripts, `#SBATCH` options, partitions,
  node specs, interactive jobs, monitoring/canceling jobs (`squeue`,
  `scancel`, `sinfo`, `scontrol`), the `/local` scratch folder.
- Software: listing/loading modules (`ml`/`module`), requesting new software
  installs.
- Open OnDemand (web portal): shell, remote desktop, Jupyter, job composer.
- Tutorials: remote VS Code, Apptainer/Singularity containers, PyTorch job
  checkpointing/requeue.
- Policies: usage policy, account/user types, infrastructure specs, support
  channels (khipu@utec.edu.pe, mesa de ayuda / service desk).

## How this skill is organized

Each file in `reference/` bundles the full extracted text of one doc section,
in the order the topics appear on the site, with a `Fuente: <url>` line above
each page's content so you can cite the original page. Read only the file(s)
relevant to the question — don't load all of them for a narrow question.

| File | Covers |
|---|---|
| `reference/00-sobre-khipu.md` | What Khipu is, cost/eligibility, citation text, infrastructure, usage policy, account/group types |
| `reference/01-primeros-pasos.md` | Requesting access, SSH login, changing password, SSH keys, transferring files, next steps |
| `reference/02-enviar-jobs-slurm.md` | Access-node rules, basic Slurm commands, `sbatch` script anatomy, partitions (specs table), nodes, `#SBATCH`/Slurm options, interactive jobs, monitoring jobs, `/local` scratch |
| `reference/03-ejemplos.md` | Worked job examples: introductory, Python, Miniconda, MPI/OpenMP |
| `reference/04-software.md` | Available software/module list, how to load/use modules, requesting new installs |
| `reference/05-open-ondemand.md` | Open OnDemand web portal: shell, desktop, job composer, Jupyter |
| `reference/06-tutoriales.md` | Remote VS Code, Apptainer, Jupyter (conda/pip), PyTorch job restart/checkpointing |
| `reference/07-soporte-anuncios.md` | Support channels, help desk, cluster status/announcements blog |

## Known gaps in the source site (as of the crawl date)

These pages exist in the site's sitemap/nav but were **empty stubs** when
scraped — don't invent content for them, tell the user the page isn't
published yet and point them to support:
- `guia-de-usuario/enviar-jobs/jobs-gpu/` ("Jobs gpu")
- `guia-de-usuario/ejemplos/gpu/` (GPU example)

The site also has older, now-superseded flat URLs (e.g.
`/guia-de-usuario/particiones/`, `/software/lista/`) that still resolve but
hold stale/shorter content; this skill only captures the current
nav-linked versions (nested under `/guia-de-usuario/enviar-jobs/...` and
`/guia-de-usuario/software/...`).

`reference/07-soporte-anuncios.md`'s "Anuncios" entry is just the blog index;
individual dated incident/maintenance posts were not captured since they're
time-bound and go stale — if the user asks about current cluster status,
tell them to check `https://docs.khipu.utec.edu.pe/anuncios/` directly.

## Refreshing this skill

Content can drift (new partitions, software, policies). To refresh, re-crawl
`https://docs.khipu.utec.edu.pe/sitemap.xml` for the current page list and
re-extract each page's text, replacing the files in `reference/`.
