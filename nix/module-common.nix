{ lib, pkgs, mkPackageOption ? null }:

{ config, ... }:

let
  inherit (lib) mkEnableOption mkIf mkOption types boolToString;

  cfg = config.services.jcalapi;

  fmtList = list: lib.concatStringsSep "," list;
  stateDir = "%S/jcalapi";
  credTarget =
    lib.optionalString (cfg.google.credentialsFile != null)
      "${stateDir}/google-credentials.json";

  pkgOption =
    if mkPackageOption == null then
      mkOption {
        type = types.package;
        default = pkgs.jcalapi;
        description = "jcalapi package to run.";
      }
    else
      mkPackageOption pkgs "jcalapi" { };

  envAttrs =
    (lib.optionalAttrs (cfg.port != null) { PORT = toString cfg.port; })
    // (lib.optionalAttrs (cfg.confluence.url != null) {
      CONFLUENCE_URL = cfg.confluence.url;
    })
    // (lib.optionalAttrs (cfg.confluence.username != null) {
      CONFLUENCE_USERNAME = cfg.confluence.username;
    })
    // (lib.optionalAttrs (cfg.confluence.password != null) {
      CONFLUENCE_PASSWORD = cfg.confluence.password;
    })
    // (lib.optionalAttrs (cfg.confluence.convertEmail != null) {
      CONFLUENCE_CONVERT_EMAIL = boolToString cfg.confluence.convertEmail;
    })
    // (lib.optionalAttrs (cfg.exchange.username != null) {
      EXCHANGE_USERNAME = cfg.exchange.username;
    })
    // (lib.optionalAttrs (cfg.exchange.password != null) {
      EXCHANGE_PASSWORD = cfg.exchange.password;
    })
    // (lib.optionalAttrs (cfg.exchange.serviceEndpoint != null) {
      EXCHANGE_SERVICE_ENDPOINT = cfg.exchange.serviceEndpoint;
    })
    // (lib.optionalAttrs (cfg.exchange.autodiscovery != null) {
      EXCHANGE_AUTODISCOVERY = boolToString cfg.exchange.autodiscovery;
    })
    // (lib.optionalAttrs (cfg.exchange.email != null) {
      EXCHANGE_EMAIL = cfg.exchange.email;
    })
    // (lib.optionalAttrs (cfg.exchange.sharedInboxes != null) {
      EXCHANGE_SHARED_INBOXES = fmtList cfg.exchange.sharedInboxes;
    })
    // (lib.optionalAttrs (cfg.google.credentialsFile != null) {
      GOOGLE_CREDENTIALS = credTarget;
    })
    // (lib.optionalAttrs (cfg.google.calendarRegex != null) {
      GOOGLE_CALENDAR_REGEX = cfg.google.calendarRegex;
    })
    // (lib.optionalAttrs (cfg.pastDaysImport != null) {
      PAST_DAYS_IMPORT = toString cfg.pastDaysImport;
    })
    // (lib.optionalAttrs (cfg.futureDaysImport != null) {
      FUTURE_DAYS_IMPORT = toString cfg.futureDaysImport;
    })
    // cfg.extraEnv;
in
{
  options.services.jcalapi = {
    enable = mkEnableOption "jcalapi calendar API user service";

    package = pkgOption;

    reloadHook = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Run a reload hook after start.";
      };

      delaySeconds = mkOption {
        type = types.ints.positive;
        default = 10;
        description = "Delay before issuing reload request.";
      };
    };

    wantedBy = mkOption {
      type = types.listOf types.str;
      default = [ "default.target" ];
      description = "Targets that should want the jcalapi user service.";
    };

    google = {
      credentialsFile = mkOption {
        type = types.nullOr types.path;
        default = null;
        description = "Path to Google credentials JSON; sets GOOGLE_CREDENTIALS.";
      };

      calendarRegex = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Regex to filter Google calendars (GOOGLE_CALENDAR_REGEX).";
      };
    };

    confluence = {
      url = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Confluence URL (CONFLUENCE_URL).";
      };

      username = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Confluence username (CONFLUENCE_USERNAME).";
      };

      password = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Confluence password/token (CONFLUENCE_PASSWORD).";
      };

      convertEmail = mkOption {
        type = types.nullOr types.bool;
        default = null;
        description = "Whether to convert Confluence usernames to emails (CONFLUENCE_CONVERT_EMAIL).";
      };
    };

    exchange = {
      username = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Exchange username (EXCHANGE_USERNAME).";
      };

      password = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Exchange password (EXCHANGE_PASSWORD).";
      };

      serviceEndpoint = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Exchange service endpoint override (EXCHANGE_SERVICE_ENDPOINT).";
      };

      autodiscovery = mkOption {
        type = types.nullOr types.bool;
        default = null;
        description = "Whether to use Exchange autodiscovery (EXCHANGE_AUTODISCOVERY).";
      };

      email = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "Exchange email (EXCHANGE_EMAIL).";
      };

      sharedInboxes = mkOption {
        type = types.nullOr (types.listOf types.str);
        default = null;
        description = "List of shared inboxes for Exchange (EXCHANGE_SHARED_INBOXES, comma-separated).";
      };
    };

    pastDaysImport = mkOption {
      type = types.nullOr types.int;
      default = null;
      description = "Past days import window (PAST_DAYS_IMPORT).";
    };

    futureDaysImport = mkOption {
      type = types.nullOr types.int;
      default = null;
      description = "Future days import window (FUTURE_DAYS_IMPORT).";
    };

    port = mkOption {
      type = types.nullOr types.int;
      default = 7042;
      description = "Port for jcalapi to listen on (PORT env var).";
    };

    extraEnv = mkOption {
      type = types.attrsOf types.str;
      default = { };
      description = "Additional environment variables to inject.";
    };

    extraEnvFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Optional EnvironmentFile to include.";
    };
  };

  config = mkIf cfg.enable {
    systemd.user.services.jcalapi = {
      Unit = {
        Description = "jcalapi calendar API (user service)";
      };
      Install.WantedBy = cfg.wantedBy;

      Service = {
        ExecStart = "${cfg.package}/bin/jcalapi";
        Restart = "on-failure";
        Environment = lib.mapAttrsToList (n: v: "${n}=${v}") envAttrs;
        EnvironmentFile = lib.optional (cfg.extraEnvFile != null) cfg.extraEnvFile;
        WorkingDirectory = stateDir;
        StateDirectory = "jcalapi";
        StateDirectoryMode = "0700";
        ExecStartPre =
          [ "${pkgs.coreutils}/bin/mkdir -p ${stateDir}" ]
          ++ (lib.optionals (cfg.google.credentialsFile != null) [
            "${pkgs.coreutils}/bin/cp --dereference ${cfg.google.credentialsFile} ${credTarget}"
            "${pkgs.coreutils}/bin/chmod 600 ${credTarget}"
          ]);
        ExecStartPost = lib.mkIf cfg.reloadHook.enable [
          "${pkgs.coreutils}/bin/sleep ${toString cfg.reloadHook.delaySeconds}"
          "${pkgs.curl}/bin/curl -X POST http://127.0.0.1:${toString cfg.port}/reload"
        ];
      };
    };
  };
}
