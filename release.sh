#!/bin/zsh
# Notarize gobrowser.app and build the goclaude disk image — v1.6.0
#
# Run ./build.sh first. Notarizes and staples dist/gobrowser.app, then builds
# dist/goclaude-<version>.dmg holding goclaude, gobrowser.app, README.md and
# LICENSE, signs it with the Developer ID, notarizes it with the PixProNotary keychain
# profile (shared with the other apps) and staples the ticket.
# This does NOT tag, push or make the GitHub release.
set -e
cd "${0:A:h}"

VERSION="1.6.0"
SIGN_ID="4208ABA3EC12F24C1F09C7BB624EFF68B44259DB"
PROFILE="PixProNotary"
DMG="dist/goclaude-${VERSION}.dmg"

xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1 \
    || { echo "error: no notary profile '$PROFILE' in keychain" >&2; exit 1; }

APP="dist/gobrowser.app"
[[ -d "$APP" ]] || { echo "error: $APP not found — run ./build.sh first" >&2; exit 1; }

echo "==> notarizing the app"
rm -f dist/gobrowser_notarize.zip
ditto -c -k --keepParent "$APP" dist/gobrowser_notarize.zip
xcrun notarytool submit dist/gobrowser_notarize.zip --keychain-profile "$PROFILE" --wait
xcrun stapler staple "$APP"
rm -f dist/gobrowser_notarize.zip

rm -rf dist/dmg "$DMG"; mkdir -p dist/dmg
cp -R "$APP" dist/dmg/
cp goclaude README.md LICENSE dist/dmg/
chmod +x dist/dmg/goclaude

# hdiutil create is deprecated and fails with "Resource busy" on this macOS;
# diskutil image create from builds the same compressed (UDZO) image.
diskutil image create from --format UDZO --volumeName "goclaude" dist/dmg "$DMG" >/dev/null
rm -rf dist/dmg

echo "==> signing and notarizing"
codesign --force --timestamp --sign "$SIGN_ID" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait
xcrun stapler staple "$DMG"

echo "==> $DMG"
codesign --verify --verbose "$DMG" 2>&1 | tail -1
echo "    stapled: $(xcrun stapler validate "$DMG" >/dev/null 2>&1 && echo YES || echo no)"
echo "    gatekeeper: $(spctl -a -t open --context context:primary-signature "$DMG" 2>&1 | tail -1)"
