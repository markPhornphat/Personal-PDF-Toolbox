# Update architecture

An installed build may contain an explicit source repository, release repository, privacy mode and Ed25519 public key. Unconfigured builds have no GitHub update client available. Automatic checks require opt-in and respect the configured interval. A manual check uses the same verification path.

The updater reads the stable release from GitHub's API using HTTPS. It accepts the configured repository, numeric asset IDs and the exact release filenames. Redirects for asset responses are restricted to GitHub's release asset hosts and strip the credential. The manifest signature covers the repository, application, version, platform, architecture, filename, byte count and digest. Only a higher stable version can be offered.

After approval, the installer is downloaded in chunks into a unique per-user folder. Cancellation or a failed check removes the staging directory. Before launch, the app verifies the file again and resolves pending editor work. Inno waits for the prior application process to exit. A relaunch checks the expected version and removes a completed download where possible. Windows publisher trust is separate from the Ed25519 mechanism. The application does not implement automated rollback.
