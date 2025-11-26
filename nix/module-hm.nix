{ config, lib, pkgs, ... }:

let
  moduleCommon =
    import ./module-common.nix {
      inherit lib pkgs;
      mkPackageOption = null;
    };
in
moduleCommon { inherit config; }
