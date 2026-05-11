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

        python = pkgs.python314;

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
          nativeBuildInputs = [
            pyPkgs."uv-build"
          ];
          pythonRelaxDeps = [
            "environs"
            "python-multipart"
            "uvicorn"
          ];
          propagatedBuildInputs = [
            pyPkgs."atlassian-python-api"
            pyPkgs.beautifulsoup4
            pyPkgs.diskcache
            pyPkgs.environs
            pyPkgs.exchangelib
            pyPkgs.fastapi
            pyPkgs.gcsa
            pyPkgs.httpx
            pyPkgs.icalendar
            pyPkgs.loguru
            pyPkgs."python-dateutil"
            pyPkgs."python-multipart"
            pyPkgs."recurring-ical-events"
            pyPkgs."typing-inspect"
            pyPkgs.uvicorn
            pyPkgs.xdg
          ];
          pythonImportsCheck = [ "jcalapi" ];
        };
      in
      {
        packages = {
          default = jcalapiPackage;
          jcalapi = jcalapiPackage;
        };

        devShells.default = pkgs.mkShell {
          name = "jcalapi-devshell";
          packages = [
            python
            devTools
            pkgs.uv
            pkgs.pre-commit
            pkgs.git
          ];
        };
      }
    )
    // {
      nixosModules.default = import ./nix/module.nix;
      homeModules.default = import ./nix/module-hm.nix;
    };
}
