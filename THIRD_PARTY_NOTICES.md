# Third-Party Notices

This repository's original program code (compiler, scaffolding, web app,
build tools) is licensed under the MIT License in [`LICENSE`](./LICENSE).
The teaching materials and other non-code content (lecture text, figures,
curriculum and design documents, generated handouts) are licensed under
CC BY-NC-SA 4.0 in [`LICENSE-MATERIALS`](./LICENSE-MATERIALS).

The project uses third-party tools and dependencies when building or running
the materials. They remain subject to their own licenses; the MIT License does
not replace those terms.

| Area | Source of dependency information |
|---|---|
| Web application | `web/app/package.json` and `web/app/package-lock.json` |
| OCaml web core | `web/core/dune-project`, `web/core/**/*.dune` |
| OCaml reference implementation | `workbook/ocaml/dune-project`, `workbook/ocaml/dune` |
| PDF build | Pandoc, TeX Live, Graphviz, Noto Sans CJK JP, and Inconsolata installed by the builder |
| Container runtime | `workbook/docker/rv64/Dockerfile` |

Before publishing a release, inspect the installed dependency licenses and add
an explicit notice here for any third-party source, font, image, or binary
copied into this repository or its release archive.
