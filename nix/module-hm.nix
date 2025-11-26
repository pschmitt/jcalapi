{ config, inputs, lib, pkgs, ... }:

let
  packageOption =
    pkgs: name: _opts:
    lib.mkOption {
      inherit (inputs.jcalapi.packages.${pkgs.stdenv.hostPlatform.system}) default;
      type = lib.types.package;
      description = "jcalapi package to run.";
    };

  moduleCommon =
    import ./module-common.nix {
      inherit lib pkgs;
      mkPackageOption = packageOption;
    };
in
moduleCommon { inherit config; }
