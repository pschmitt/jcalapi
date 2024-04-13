{ ... }:

{
  languages.nix.enable = true;
  languages.python.enable = true;

  languages.python.poetry = {
    enable = true;
    activate = {
      enable = true;
    };
  };

  pre-commit.hooks = {
    black.enable = true;
    # isort.enable = true;
  };

  devcontainer.enable = true;
}
