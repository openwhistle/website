# Invariants

Reference: which test holds which guard of the site, and what breaking it looks like. Every row was
verified by mutation (`scripts/mutation_audit.py`, the specs in `docs-tech/mutations/`). The app's
guards: `docs-tech/invariants.md` in openwhistle/OpenWhistle, where these rows began.

## The site and the latest app release

`docs-tech/mutations/v2.2.0-site-split.json` (`docs-tech/specs/2026-10-09-website-repo-split-design.md`).
The release is read by `scripts/release_source.py`; a mutation of `tests/fixtures/app_source/` stands
for a release that changed.

| Mutation | File | Test that fires |
| --- | --- | --- |
| `SETTING-UNDOCUMENTED` | `docs/_data/config.yml` | `test_config_yml_lists_every_setting_once_and_nothing_else` |
| `STATUSES-STALE-IN-GUIDE`, `DARK-ALT-DROPS-A-TRANSITION` | `docs/en/docs/admin/index.html` | `test_the_admin_guide_describes_exactly_the_report_statuses_and_transitions` |
| `FONT-DIVERGES` | `docs/fonts/sora-LICENSE` | `test_every_shared_file_is_the_releases` |
| `DESIGN-MD-DIVERGES` | `DESIGN.md` | `test_every_shared_file_is_the_releases` |
| `MARK-DIVERGES` | `scripts/render_icons.py` | `test_the_mark_is_the_releases_geometry`, `test_every_copy_draws_the_one_geometry` |
| `VERSION-FROM-ELSEWHERE` | `scripts/build_site.py` | `test_the_footer_shows_the_app_version` |
| `CHANGELOG-FROM-ELSEWHERE` | `scripts/build_site.py` | `test_the_changelog_is_the_releases` |
| `EDIT-LINK-TO-APP-REPO` | `scripts/build_site.py` | `test_the_docs_layout_builds_sidebar_toc_pager_and_edit_link` |
| `FETCH-TAKES-EVERYTHING` | `scripts/release_source.py` | `test_the_fetch_takes_exactly_the_files_the_site_reads` |
| `TOKEN-TO-RAW-HOST` | `scripts/release_source.py` | `test_the_token_goes_to_the_api_only` |
| `OVERRIDE-MISREAD` | `scripts/release_source.py` | every fixture test of `tests/test_release_source.py` |
| `TRUNCATED-TREE-ACCEPTED` | `scripts/release_source.py` | `test_a_truncated_tree_is_refused` |
| `HALF-FETCH-KEPT` | `scripts/release_source.py` | `test_the_fetch_takes_exactly_the_files_the_site_reads` |
| `ROUTE-METHODS-UNRESOLVED` | `scripts/release_source.py` | `test_routes_cover_every_registration_form` |
| `AUDIT-SHARED-PYC` | `scripts/mutation_audit.py` | `test_every_audit_run_gets_its_own_bytecode_cache` |
| `AUDIT-CRASHES-ON-A-GONE-FILE` | `scripts/mutation_audit.py` | `test_the_audit_reports_red_green_and_stale` |
| `DOCS-TECH-CONTENT-LEAK` | `docs/assets/site-css.txt` (a copy of `docs-tech/site-css.md`) | `test_no_built_file_comes_from_docs_tech` |
| `TAG-UNVALIDATED` | `scripts/release_source.py` | `test_a_tag_that_is_no_release_version_is_refused` |
| `PINNED-TAG-IGNORED` | `scripts/release_source.py` | `test_a_pinned_tag_is_fetched_without_asking_for_the_latest` |
| `CACHE-IGNORES-FETCH-LIST` | `scripts/release_source.py` | `test_a_cache_fetched_with_another_list_is_fetched_again` |
| `TREE-SPLIT-ON-SPACE` | `scripts/release_source.py` | `test_a_fetched_release_is_read_by_tag_tree_and_date` |
| `RELATIVE-OUTSIDE-UNCHECKED` | `scripts/release_source.py` | `test_relative_outside_the_working_directory_fails_loudly` |
| `PUBLISH-REFETCHES-LATEST` | `.github/workflows/website-image.yml` | `test_publish_builds_exactly_the_release_the_tests_tested` |
| `PUBLISH-EMPTY-TAG-ALLOWED` | `.github/workflows/website-image.yml` | `test_publish_builds_exactly_the_release_the_tests_tested` |
| `IDENTITY-OTHER-REPO` | `.github/workflows/website-image.yml` | `test_the_image_is_signed_with_sbom_and_provenance_for_the_amd64_target` |
| `INLINE-PIN-SCAN-BLIND` | `tests/test_renovate.py` | `test_the_inline_pin_scan_sees_a_docker_run_and_skips_actions` |
| `HISTORY-SPEC-LIVE` | `docs-tech/mutations/v2.1.0-site-p1.json` | `test_every_mutation_matches_its_file_exactly_once` |
| `IMAGE-BUILDS-ANOTHER-RELEASE` | `.github/workflows/website-image.yml` | `test_the_tests_and_the_image_read_one_fetched_release` |
| `LIFECYCLE-EDGES` (`v2.1.1-site-p2a.json`) | `docs/_diagrams/case-lifecycle.drawio` | `test_the_case_lifecycle_draws_exactly_the_status_transitions` |
| `FAVICONS-DIVERGE` (`v2.1.1-site-p2b.json`) | `tests/fixtures/app_source/app/static/favicon.svg` | `test_the_fixture_mark_and_favicon_are_the_sites` |
| `DEMO-COOKIE-NEW` (`v2.1.2-site-p3.json`) | `tests/fixtures/app_source/app/api/reports.py` | `test_the_cookie_scan_reads_every_set_cookie_of_the_release` |
| `WEEKLY-RELEASE-RUN` (`v2.1.2-site-p4.json`) | `.github/workflows/website-image.yml` | `test_a_new_app_release_is_built_within_a_week` |

## Rows carried over from the app's invariants

| Mutation | File | Test that fires |
| --- | --- | --- |
| `review-matrix-drops-a-site-page` | `docs-tech/local-review.md` | `test_local_review_page_matrix_covers_every_docs_site_page` |
| `docs-link-into-docs-tech` | `docs/en/docs/*/index.html`, `docs/_data/config.yml` | `test_no_published_page_links_docs_tech` |
| `docs-env-table-unscrolled` | `scripts/build_site.py` (`config_table`) | `test_docs_page_has_no_horizontal_overflow` |
| `de-token-drift` | `docs/de/index.html` | `test_only_tokens_css_defines_custom_properties` (since 2.1.1 the tokens exist once, in `tokens.css`) |
| `de-faq-jsonld-drift` | `docs/de/index.html` | `test_faqpage_jsonld_matches_visible_faq_one_to_one` |
| `en-hreflang-de-dropped` | `docs/en/index.html` | `test_landing_pages_link_each_other_via_hreflang` |
| `de-hreflang-default-dropped` | `docs/de/index.html` | `test_landing_pages_link_each_other_via_hreflang` |
| `de-comparison-table-auto` | `docs/de/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `de-btn-nowrap` | `docs/de/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `docs-nav-blog-missing` | `docs/_data/nav.yml` | `test_every_docs_page_nav_has_the_same_item_set` |
| `roadmap-nav-current-unmarked` | `docs/en/roadmap/index.html` | `test_current_nav_item_is_marked` |
| `roadmap-footer-issues-missing` | `docs/en/roadmap/index.html` | `test_every_page_footer_has_the_same_link_set_as_its_landing_page` |
| `blog-token-drift` | `docs/de/blog/index.html` | `test_only_tokens_css_defines_custom_properties` (since 2.1.1 the tokens exist once, in `tokens.css`) |
| `nav-collapse-768-en` | `docs/en/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-de` | `docs/de/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-docs` | `docs/assets/css/base.css` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-roadmap` | `docs/en/roadmap/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-blog` | `docs/de/blog/index.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-hinschg-compliance-leitfaden` | `docs/de/blog/hinschg-compliance-leitfaden.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-interne-meldestelle-einrichten` | `docs/de/blog/interne-meldestelle-einrichten.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-was-ist-neu-in-2-0` | `docs/de/blog/was-ist-neu-in-2-0.html` | `test_docs_page_has_no_horizontal_overflow` |
| `nav-collapse-768-whistleblower-software-vergleich` | `docs/de/blog/whistleblower-software-vergleich.html` | `test_docs_page_has_no_horizontal_overflow` |
| `docs-mono-500-face-missing` | `docs/assets/css/fonts.css` | `test_every_docs_page_font_usage_has_a_matching_font_face` |
| `roadmap-mono-500-face-missing` | `docs/en/roadmap/index.html` | `test_every_docs_page_font_usage_has_a_matching_font_face` |
| `blog-deadline-table-auto` | `docs/de/blog/hinschg-compliance-leitfaden.html` | `test_docs_page_has_no_horizontal_overflow` |
| `blog-2-0-date-off-by-one` | `docs/de/blog/was-ist-neu-in-2-0.html` | `test_blog_1_6_release_date_is_2026_09_26` |
| `rollback-pins-old-image` | `docs/en/docs/upgrade/index.html` | `test_the_documented_rollback_downgrades_to_the_last_1_5_revision` |
| `docs-python-m-app` | `docs/en/docs/rotate-key/index.html`, `docs/en/docs/lost-authenticator/index.html` | `test_the_docs_run_no_module_that_does_not_exist` |
| `docs-link-docs-tech` | `docs/en/docs/*/index.html`, `docs/_data/config.yml` | `test_no_published_page_links_docs_tech` |
| `roadmap-test-chore` | `docs/en/roadmap/index.html` | `test_the_public_roadmap_holds_no_test_chores` |
