{
  description = "Flake for jcalapi development and packaging";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };

        python = pkgs.python313.override {
          packageOverrides = final: prev: {
            asynccli = prev.buildPythonPackage {
              pname = "asynccli";
              version = "0.1.3";
              format = "setuptools";
              src = pkgs.fetchurl {
                url = "https://files.pythonhosted.org/packages/57/f8/c4a2cef122af5a6eafc6d468346e1625b07713ea7ee8ab90caa27d47bc96/asynccli-0.1.3.tar.gz";
                hash = "sha256-w2A/gIVtiYKBfw8vy+BCmXUkIHjhu64+ls1JF/IMTCo=";
              };
              nativeBuildInputs = [
                prev.setuptools
                prev.wheel
              ];
              doCheck = false;
              postPatch = ''
                substituteInPlace setup.py \
                  --replace "'pytest-runner'," "" \
                  --replace '"pytest-runner",' ""
              '';
              pythonImportsCheck = [ "asynccli" ];
            };

            "fastapi-utils" = prev.buildPythonPackage {
              pname = "fastapi-utils";
              version = "0.2.1";
              format = "pyproject";
              src = pkgs.fetchurl {
                url = "https://files.pythonhosted.org/packages/e6/c9/d7d8908902afb3fae40d4713b4a72848bc015e21c5c4bebfb935708b21b9/fastapi-utils-0.2.1.tar.gz";
                hash = "sha256-Dmx/wYcLgOaBSUlXq/ZdT09C9Mf3AAWRjpGBsi8b11k=";
              };
              nativeBuildInputs = [
                prev.poetry-core
                prev.pythonRelaxDepsHook
              ];
              postPatch = ''
                substituteInPlace pyproject.toml \
                  --replace "poetry>=0.12" "poetry-core>=1.0.0" \
                  --replace "poetry.masonry.api" "poetry.core.masonry.api"
              '';
              doCheck = false;
              pythonRelaxDeps = [
                "pydantic"
                "sqlalchemy"
              ];
              pythonRelaxDepsCheck = [
                "pydantic"
                "sqlalchemy"
              ];
              propagatedBuildInputs = with prev; [
                fastapi
                pydantic
                python-dateutil
                sqlalchemy
                typing-extensions
              ];
              pythonImportsCheck = [ "fastapi_utils" ];
            };
          };
        };

        pyPkgs = python.pkgs;

        devTools = python.withPackages (
          ps: with ps; [
            black
            flake8
            ipython
            isort
            uv
          ]
        );

        jcalapiPackage = pyPkgs.buildPythonApplication {
          pname = "jcalapi";
          version = "0.1.9";
          src = ./.;
          pyproject = true;
          nativeBuildInputs = [ pyPkgs."uv-build" ];
          propagatedBuildInputs =
            let
              atlassianPythonApi = pyPkgs."atlassian-python-api";
              fastapiUtils = pyPkgs."fastapi-utils";
              recurringIcalEvents = pyPkgs."recurring-ical-events";
              pythonMultipart = pyPkgs."python-multipart";
              uvicornPkg = pyPkgs.uvicorn;
            in
            [
              pyPkgs.asynccli
              atlassianPythonApi
              pyPkgs.beautifulsoup4
              pyPkgs.diskcache
              pyPkgs.environs
              pyPkgs.exchangelib
              pyPkgs.fastapi
              fastapiUtils
              pyPkgs.gcsa
              pyPkgs.httpx
              pyPkgs.icalendar
              pyPkgs.loguru
              pyPkgs.python-dateutil
              pythonMultipart
              recurringIcalEvents
              pyPkgs.typing-inspect
              uvicornPkg
              pyPkgs.xdg
            ];
          pythonImportsCheck = [ "jcalapi" ];
        };
      in
      {
        packages.default = jcalapiPackage;

        devShells.default = pkgs.mkShell {
          name = "jcalapi-devshell";
          packages = [
            python
            devTools
            pkgs.uv
            pkgs.pre-commit
            pkgs.git
          ];

          shellHook = ''
            export PYTHONPATH="''${PWD}/src:''${PYTHONPATH:-}"
            export UV_PROJECT_ENVIRONMENT=".venv"
            echo "Entering jcalapi dev shell with Python ${python.version} and uv available."
            echo "Dev tools are available; run 'uv sync' if you need local deps, then 'uv run python -m jcalapi'."
          '';
        };
      }
    );
}
