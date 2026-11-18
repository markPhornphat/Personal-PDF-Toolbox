# Changelog

## 0.3.1

- The PDF to Word schematic now shows header and footer bands rendered by Word, preserving left/right placement, tab stops, formatting, supported inline artwork, and odd/even page variations.
- PDF to Word now uses separate drop areas, compact reorderable PDF cards, centered image placement defaults, smoother progress, and a completion dialog.
- Added a mascot loading screen at startup and clearer warning dialogs across the app. Page lists now use workspace order while retaining the source page in the tooltip.

## 0.3.0

- Added local batch PDF-to-Word conversion with ordered PDF intake, placement controls, a bounded schematic preview, progress and cancellation. Microsoft Word Desktop is required for this mode.
- Added isolated Word automation, original-package preservation, embedded images and validation of page counts, image placement, original content, source integrity and reopening.
- Added pinned pywin32 and bundled COM runtime support. Existing PDF tools and the opt-in updater retain their existing boundaries.
- Verified the automated suite and four real Word integration cases. Header/footer tables, floating objects and other unmeasurable layouts are rejected safely; broader document-corpus and clean-machine acceptance remain pending. See `docs/PDF_TO_WORD_TEST_REPORT.md`.

## 0.2.1

- Added an illustrated About dialog and centered the theme shortcut beside Settings.
- Added startup update checks once per day or Windows boot, a bottom-right notice, and automatic verified silent installation and restart from Update now.
- Added loading and result feedback to update checks in About and Settings.

## 0.2.0

- Added Organize PDF with rotation, blank A4 pages, reverse order, page-range insertion, reordering, and undo and redo.
- Added pink accents, pointer cursors on buttons, and a brief tool-icon transition that follows the Windows animation setting.

## 0.1.4

- Added dedicated empty pages with PDF drop fields for all five tools.
- Added a theme menu beside Settings and localized hover descriptions for app buttons.

## 0.1.3

- Added a walking dog to the PDF processing dialog, with page progress and cancellation.
- Fixed sidebar navigation and made Home file paste open actionable tool choices.
- Kept page captions visible while thumbnails load and added icons to tool actions.

## 0.1.2

- Redesigned the desktop interface in both themes, with a dog mascot on Home, active navigation, and searchable tool cards.
- Improved thumbnail captions, page navigation, the editor inspector, and settings layout.

## 0.1.1

- Localized the PDF tools, settings, prompts, and feedback in Thai, with a Thai user guide.
- Preserved the original Unicode of Thai editor text for readers that honor PDF replacement text.

## 0.1.0

- Added five local PDF workspaces for merging, splitting, page extraction, image conversion and visual editing.
- Added page previews, file drag and drop, clipboard input, and safe staged exports.
- Added a Windows offline installer and opt-in signed GitHub updates for configured builds.
