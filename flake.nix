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
          version = "0.2.0";
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
          propagatedBuildInputs = with pyPkgs; [
            pyPkgs."atlassian-python-api"
            beautifulsoup4
            diskcache
            environs
            exchangelib
            fastapi
            gcsa
            httpx
            icalendar
            loguru
            pyPkgs."python-dateutil"
            pyPkgs."python-multipart"
            pyPkgs."recurring-ical-events"
            pyPkgs."typing-inspect"
            uvicorn
            xdg
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
