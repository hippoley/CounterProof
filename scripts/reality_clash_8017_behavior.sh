#!/usr/bin/env bash
set -euo pipefail

: "${CANDIDATE:?CANDIDATE required}"
: "${CANDIDATE_REPO:?CANDIDATE_REPO required}"
: "${CANDIDATE_SHA:?CANDIDATE_SHA required}"

work="$RUNNER_TEMP/clash-8017-${CANDIDATE}"
rm -rf "$work"
git clone --filter=blob:none "$CANDIDATE_REPO" "$work"
cd "$work"
git checkout --detach "$CANDIDATE_SHA"
test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"

# Tauri's build script validates the configured external binary path even for library tests.
# The probe never executes this sidecar; an empty executable placeholder is sufficient to
# let the upstream Rust test target compile without altering application code paths.
mkdir -p src-tauri/sidecar
for bin in \
  clash-verge-service \
  clash-verge-service-install \
  clash-verge-service-uninstall \
  verge-mihomo \
  verge-mihomo-alpha
do
  touch "src-tauri/sidecar/${bin}-x86_64-unknown-linux-gnu"
  chmod +x "src-tauri/sidecar/${bin}-x86_64-unknown-linux-gnu"
done

python3 - <<'PY'
from pathlib import Path

path = Path("src-tauri/src/config/config.rs")
source = path.read_text()
probe = r'''

#[cfg(all(test, target_os = "linux"))]
mod counterproof_exit_save_probe {
    use super::Config;
    use crate::utils::dirs;
    use std::{
        fs,
        os::unix::fs::MetadataExt,
        time::{Duration, SystemTime, UNIX_EPOCH},
    };

    struct Fingerprint {
        bytes: Vec<u8>,
        inode: u64,
        modified_ns: u128,
    }

    fn fingerprint(path: &std::path::Path) -> Fingerprint {
        let metadata = fs::metadata(path).expect("metadata");
        let modified_ns = metadata
            .modified()
            .unwrap_or(SystemTime::UNIX_EPOCH)
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        Fingerprint {
            bytes: fs::read(path).expect("read config"),
            inode: metadata.ino(),
            modified_ns,
        }
    }

    fn changed(before: &Fingerprint, after: &Fingerprint) -> bool {
        before.bytes != after.bytes
            || before.inode != after.inode
            || before.modified_ns != after.modified_ns
    }

    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn counterproof_no_staged_exit_write() {
        let app_home = dirs::app_home_dir().expect("app home");
        fs::create_dir_all(&app_home).expect("create app home");

        let verge = Config::verge().await;
        verge.data_arc().save_file().await.expect("seed verge.yaml");
        let path = dirs::verge_path().expect("verge path");
        let before = fingerprint(&path);

        tokio::time::sleep(Duration::from_millis(1200)).await;
        Config::apply_all_and_save_file().await;

        let after = fingerprint(&path);
        println!(
            "COUNTERPROOF_NO_STAGE changed={} inode_before={} inode_after={} mtime_before={} mtime_after={} bytes_changed={}",
            changed(&before, &after),
            before.inode,
            after.inode,
            before.modified_ns,
            after.modified_ns,
            before.bytes != after.bytes,
        );
    }

    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn counterproof_staged_exit_write() {
        let app_home = dirs::app_home_dir().expect("app home");
        fs::create_dir_all(&app_home).expect("create app home");

        let verge = Config::verge().await;
        verge.data_arc().save_file().await.expect("seed verge.yaml");
        let path = dirs::verge_path().expect("verge path");
        let before = fingerprint(&path);

        verge.edit_draft(|draft| {
            draft.enable_tun_mode = Some(false);
        });

        tokio::time::sleep(Duration::from_millis(1200)).await;
        Config::apply_all_and_save_file().await;

        let after = fingerprint(&path);
        println!(
            "COUNTERPROOF_STAGED changed={} inode_before={} inode_after={} mtime_before={} mtime_after={} bytes_changed={}",
            changed(&before, &after),
            before.inode,
            after.inode,
            before.modified_ns,
            after.modified_ns,
            before.bytes != after.bytes,
        );
        assert!(changed(&before, &after), "staged draft must cause observable save");
    }
}
'''
if "counterproof_exit_save_probe" in source:
    raise SystemExit("probe already present")
path.write_text(source + probe)
PY

cd src-tauri

export XDG_DATA_HOME="$RUNNER_TEMP/counterproof-${CANDIDATE}-no-stage"
rm -rf "$XDG_DATA_HOME"
mkdir -p "$XDG_DATA_HOME"
cargo test --lib counterproof_no_staged_exit_write -- --nocapture | tee "$RUNNER_TEMP/no-stage-${CANDIDATE}.log"
grep 'COUNTERPROOF_NO_STAGE' "$RUNNER_TEMP/no-stage-${CANDIDATE}.log" | tee "$RUNNER_TEMP/no-stage-${CANDIDATE}.result"

export XDG_DATA_HOME="$RUNNER_TEMP/counterproof-${CANDIDATE}-staged"
rm -rf "$XDG_DATA_HOME"
mkdir -p "$XDG_DATA_HOME"
cargo test --lib counterproof_staged_exit_write -- --nocapture | tee "$RUNNER_TEMP/staged-${CANDIDATE}.log"
grep 'COUNTERPROOF_STAGED' "$RUNNER_TEMP/staged-${CANDIDATE}.log" | tee "$RUNNER_TEMP/staged-${CANDIDATE}.result"

{
  echo "## $CANDIDATE"
  echo
  echo "Exact candidate: `$CANDIDATE_SHA`"
  echo
  echo "### No staged draft"
  echo '~~~text'
  cat "$RUNNER_TEMP/no-stage-${CANDIDATE}.result"
  echo '~~~'
  echo
  echo "### Staged draft"
  echo '~~~text'
  cat "$RUNNER_TEMP/staged-${CANDIDATE}.result"
  echo '~~~'
} >> "$GITHUB_STEP_SUMMARY"
