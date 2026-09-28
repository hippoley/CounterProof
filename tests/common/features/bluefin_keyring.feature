@common @bluefin @regression
Feature: Login keyring behavior after GNOME autologin
  The user-facing invariant is stronger than a systemd ordering check:
  when the automatic-login GNOME session is ready, the login keyring must
  already be unlocked.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Secret Service login collection is unlocked after automatic login
    * Run SSH command: "gdbus call --session --dest org.freedesktop.secrets --object-path /org/freedesktop/secrets --method org.freedesktop.Secret.Service.ReadAlias login"
    * SSH command return code is "0"
    * SSH command output contains "/org/freedesktop/secrets/collection/"
    * Run SSH command: "LOGIN_COLLECTION=$(gdbus call --session --dest org.freedesktop.secrets --object-path /org/freedesktop/secrets --method org.freedesktop.Secret.Service.ReadAlias login | sed -n \"s/.*objectpath '\\([^']*\\)'.*/\\1/p\"); test -n \"$LOGIN_COLLECTION\" && gdbus call --session --dest org.freedesktop.secrets --object-path \"$LOGIN_COLLECTION\" --method org.freedesktop.DBus.Properties.Get org.freedesktop.Secret.Collection Locked"
    * SSH command return code is "0"
    * SSH command output contains "<false>"
