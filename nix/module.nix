{ config, lib, ... }:

let
  moduleCommon = import ./module-common.nix {
    inherit (lib) pkgs;
    inherit (lib) mkPackageOption;
  };
in
moduleCommon { inherit config; }
