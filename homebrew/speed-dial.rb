# Homebrew Cask formula for SpeedDial
#
# To use this:
# 1. Place this file at: Casks/speed-dial.rb in surya-prakash-susarla/homebrew-tap
# 2. Users install with:
#      brew tap surya-prakash-susarla/tap
#      brew install --cask speed-dial
#
# After each GitHub release, release.sh updates version and sha256 automatically.
# Then copy this file to the homebrew-tap repo and push.

cask "speed-dial" do
  version "0.1.0"
  sha256 "placeholder_run_build_and_release_to_populate"

  url "https://github.com/surya-prakash-susarla/SpeedDial/releases/download/v#{version}/SpeedDial.zip"
  name "SpeedDial"
  desc "Menu bar window switcher with numeric hotkeys for macOS"
  homepage "https://github.com/surya-prakash-susarla/SpeedDial"

  app "SpeedDial.app"

  zap trash: [
    "~/Library/LaunchAgents/com.suryaprakash.speeddial.plist",
  ]
end
