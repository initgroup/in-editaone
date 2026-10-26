import unittest
from unittest.mock import Mock, patch

from backend.branding import DEFAULT_LOGO, PRODUCT_DESCRIPTION, display_branding
from backend.routers import M91002


class BrandingCompatibilityTests(unittest.TestCase):
    def test_previous_defaults_render_as_current_brand(self):
        for name in ("", "IN-DEPS", "인뎁스", "INIT Data Editing System", "INIT-Data Editing Platform System"):
            with self.subTest(name=name):
                self.assertEqual(display_branding(name, "./assets/indeps_compact_en_white.png"), {
                    "systemDisplayName": PRODUCT_DESCRIPTION, "systemLogoImage": DEFAULT_LOGO,
                })

    def test_custom_names_and_external_logos_remain_unchanged(self):
        self.assertEqual(display_branding("Customer workspace", "https://example.org/indeps_compact_en.png"), {
            "systemDisplayName": "Customer workspace", "systemLogoImage": "https://example.org/indeps_compact_en.png",
        })

    def test_display_endpoint_only_reads_settings_and_closes_resources(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [("INIT-Data Editing Platform System",), ("./assets/indeps_compact_en_white.png",)]
        with (patch.object(M91002, "get_request_user_id", return_value=7),
              patch.object(M91002, "get_target_connection_id", return_value=8),
              patch.object(M91002, "get_db_connection", return_value=connection),
              patch.object(M91002, "ensure_connection_owner") as owner,
              patch.object(M91002.SqlLoader, "get_sql", return_value="existing-read-query") as sql):
            result = M91002.get_display_settings(Mock())
        owner.assert_called_once_with(connection, 7, 8)
        self.assertEqual(result["data"], display_branding())
        self.assertEqual(sql.call_count, 2)
        self.assertTrue(all(call.args == ("M91002_ACTIVE_SETTING_VALUE",) for call in sql.call_args_list))
        connection.commit.assert_not_called()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()
