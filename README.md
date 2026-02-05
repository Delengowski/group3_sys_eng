# Systems Engineering

This repositories houses the work for my final project for the course Systems Engineering being offered at Rowan University during Spring 2026.

# Building Paper

The included shell script `build_tex.sh` will run `tex/Dockerfile` and copy the artifacts to `tex/build_artifacts`.


# Development

Please see the official [Docker documentation](https://daniel.es/blog/how-to-install-docker-in-wsl-without-docker-desktop/#how-to-install-docker-in-wsl-without-installing-docker-desktop) for setup. Expectation is use WSL on Windows to build latex. 

The main tex document is located in `./tex/main.tex`. Citations should be placed into `./tex/main_paper.bib` and referenced in `main.tex` by using the appropriate tex syntax e.g `\cite{<name given to citation in .bib>}`. 
