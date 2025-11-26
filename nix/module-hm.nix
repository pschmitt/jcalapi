{ config, inputs, lib, pkgs, ... }:

let
  packageOption =
    pkgs: name: _opts:
    lib.mkOption {
      type = lib.types.package;
      default = inputs.jcalapi.packages.${pkgs.system}.default;
      description = "jcalapi package to run.";
    };

  moduleCommon =
    import ./module-common.nix {
      inherit lib pkgs;
      mkPackageOption = packageOption;
    };
in
moduleCommon { inherit config; }
