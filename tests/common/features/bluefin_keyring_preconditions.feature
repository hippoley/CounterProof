@common @bluefin @regression
Feature: Login keyring oracle preconditions
  A missing login collection in the synthetic CI account is a fixture gap,
  not evidence that a candidate regressed the product.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: Secret Service is reachable in the real user session
    * Run SSH command: "gdbus introspect --session --dest org.freedesktop.secrets --object-path /org/freedesktop/secrets >/dev/null"
    * SSH command return code is "0"

  @requires_login_collection
  Scenario: Login collection exists after automatic login
    * Run SSH command: "gdbus call --session --dest org.freedesktop.secrets --object-path /org/freedesktop/secrets --method org.freedesktop.Secret.Service.ReadAlias login"
    * SSH command return code is "0"
    * SSH command output contains "/org/freedesktop/secrets/collection/"
