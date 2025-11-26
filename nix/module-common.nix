{ lib, pkgs, mkPackageOption ? null }:

{ config, ... }:

let
  inherit (lib) mkEnableOption mkIf mkOption types boolToString;

  cfg = config.services.jcalapi;

  fmtList = list: lib.concatStringsSep "," list;

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
    lib.filterAttrs (_: v: v != null) (
      {
        PORT = cfg.port;
        CONFLUENCE_URL = cfg.confluenceUrl;
        CONFLUENCE_USERNAME = cfg.confluenceUsername;
        CONFLUENCE_PASSWORD = cfg.confluencePassword;
        CONFLUENCE_CONVERT_EMAIL =
          lib.optionalString (cfg.confluenceConvertEmail != null)
            (boolToString cfg.confluenceConvertEmail);

        EXCHANGE_USERNAME = cfg.exchangeUsername;
        EXCHANGE_PASSWORD = cfg.exchangePassword;
        EXCHANGE_SERVICE_ENDPOINT = cfg.exchangeServiceEndpoint;
        EXCHANGE_AUTODISCOVERY =
          lib.optionalString (cfg.exchangeAutodiscovery != null)
            (boolToString cfg.exchangeAutodiscovery);
        EXCHANGE_EMAIL = cfg.exchangeEmail;
        EXCHANGE_SHARED_INBOXES =
          lib.optionalString (cfg.exchangeSharedInboxes != null)
            (fmtList cfg.exchangeSharedInboxes);

        GOOGLE_CREDENTIALS = cfg.googleCredentialsFile;
        GOOGLE_CALENDAR_REGEX = cfg.googleCalendarRegex;

        PAST_DAYS_IMPORT =
          lib.optionalString (cfg.pastDaysImport != null)
            (toString cfg.pastDaysImport);
        FUTURE_DAYS_IMPORT =
          lib.optionalString (cfg.futureDaysImport != null)
            (toString cfg.futureDaysImport);
      }
      // cfg.extraEnv
    );
in
{
  options.services.jcalapi = {
    enable = mkEnableOption "jcalapi calendar API user service";

    package = pkgOption;

    googleCredentialsFile = mkOption {
      type = types.nullOr types.path;
      default = null;
      description = "Path to Google credentials JSON; sets GOOGLE_CREDENTIALS.";
    };

    googleCalendarRegex = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Regex to filter Google calendars (GOOGLE_CALENDAR_REGEX).";
    };

    confluenceUrl = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Confluence URL (CONFLUENCE_URL).";
    };

    confluenceUsername = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Confluence username (CONFLUENCE_USERNAME).";
    };

    confluencePassword = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Confluence password/token (CONFLUENCE_PASSWORD).";
    };

    confluenceConvertEmail = mkOption {
      type = types.nullOr types.bool;
      default = null;
      description = "Whether to convert Confluence usernames to emails (CONFLUENCE_CONVERT_EMAIL).";
    };

    exchangeUsername = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Exchange username (EXCHANGE_USERNAME).";
    };

    exchangePassword = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Exchange password (EXCHANGE_PASSWORD).";
    };

    exchangeServiceEndpoint = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Exchange service endpoint override (EXCHANGE_SERVICE_ENDPOINT).";
    };

    exchangeAutodiscovery = mkOption {
      type = types.nullOr types.bool;
      default = null;
      description = "Whether to use Exchange autodiscovery (EXCHANGE_AUTODISCOVERY).";
    };

    exchangeEmail = mkOption {
      type = types.nullOr types.str;
      default = null;
      description = "Exchange email (EXCHANGE_EMAIL).";
    };

    exchangeSharedInboxes = mkOption {
      type = types.nullOr (types.listOf types.str);
      default = null;
      description = "List of shared inboxes for Exchange (EXCHANGE_SHARED_INBOXES, comma-separated).";
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
      default = null;
      description = "Port for jcalapi to listen on (PORT env var).";
    };

    extraEnv = mkOption {
      type = types.attrsOf types.str;
      default = { };
      description = "Additional environment variables to inject.";
    };
  };

  config = mkIf cfg.enable {
    systemd.user.services.jcalapi = {
      description = "jcalapi calendar API (user service)";
      wantedBy = [ "default.target" ];

      serviceConfig = {
        ExecStart = "${cfg.package}/bin/jcalapi";
        Restart = "on-failure";
        Environment = lib.mapAttrsToList (n: v: "${n}=${v}") envAttrs;
        WorkingDirectory = "%h/.local/share/jcalapi";
        StateDirectory = "jcalapi";
        StateDirectoryMode = "0700";
      };
    };
  };
}
