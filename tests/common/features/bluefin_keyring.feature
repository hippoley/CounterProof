@common @bluefin @regression
Feature: Login keyring behavior after GNOME autologin
  These checks are meaningful only after the companion precondition feature
  establishes that Secret Service and the login collection exist.

  Background:
    * Bluefin VM is booted and reachable over SSH

  @requires_login_collection
  Scenario: Login collection is unlocked after automatic login
    * Run SSH command: "LOGIN_COLLECTION=$(gdbus call --session --dest org.freedesktop.secrets --object-path /org/freedesktop/secrets --method org.freedesktop.Secret.Service.ReadAlias login | sed -n \"s/.*objectpath '\\([^']*\\)'.*/\\1/p\"); test -n \"$LOGIN_COLLECTION\" && gdbus call --session --dest org.freedesktop.secrets --object-path \"$LOGIN_COLLECTION\" --method org.freedesktop.DBus.Properties.Get org.freedesktop.Secret.Collection Locked"
    * SSH command return code is "0"
    * SSH command output contains "<false>"

  Scenario: Keyring does not report the historical late-session initialization error
    * Run SSH command: "journalctl --user -b --no-pager -o cat 2>/dev/null | grep -E 'gnome-keyring-daemon.*NotInInitialization' || true"
    * SSH command return code is "0"
    * SSH command output does not contain "NotInInitialization"


  Scenario: Capture CounterProof keyring causal diagnostics
    * Capture CounterProof keyring causal diagnostics
