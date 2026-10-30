#!/bin/zsh
# Sign, notarize and staple the go.claude disk image — v1.0.1
#
# Builds dist/go.claude-<version>.dmg holding go.claude, README.md and LICENSE,
# signs it with the Developer ID, notarizes it with the PixProNotary keychain
# profile (shared with the other apps) and staples the ticket.
# This does NOT tag, push or make the GitHub release.
set -e
cd "${0:A:h}"

VERSION="1.0.1"
SIGN_ID="4208ABA3EC12F24C1F09C7BB624EFF68B44259DB"
PROFILE="PixProNotary"
DMG="dist/go.claude-${VERSION}.dmg"

xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1 \
    || { echo "error: no notary profile '$PROFILE' in keychain" >&2; exit 1; }

rm -rf dist; mkdir -p dist/dmg
cp go.claude README.md LICENSE dist/dmg/
chmod +x dist/dmg/go.claude

# hdiutil create is deprecated and fails with "Resource busy" on this macOS;
# diskutil image create from builds the same compressed (UDZO) image.
diskutil image create from --format UDZO --volumeName "go.claude" dist/dmg "$DMG" >/dev/null
rm -rf dist/dmg

echo "==> signing and notarizing"
codesign --force --timestamp --sign "$SIGN_ID" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait
xcrun stapler staple "$DMG"

echo "==> $DMG"
codesign --verify --verbose "$DMG" 2>&1 | tail -1
echo "    stapled: $(xcrun stapler validate "$DMG" >/dev/null 2>&1 && echo YES || echo no)"
echo "    gatekeeper: $(spctl -a -t open --context context:primary-signature "$DMG" 2>&1 | tail -1)"
