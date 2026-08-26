from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from initiatives.models import Category, Initiative

from .forms import EmailChangeRequestForm, RegistrationForm
from .models import AuditLog
from .services import block_user, soft_delete_user, unblock_user


TEST_PASSWORD = "DemoTest2026!"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationAndEmailChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="existing.user",
            email="existing@example.com",
            password=TEST_PASSWORD,
        )

    def registration_data(self, **overrides):
        data = {
            "username": "demo.person",
            "first_name": "Иван",
            "last_name": "Петров",
            "email": "demo.person@example.com",
            "password1": TEST_PASSWORD,
            "password2": TEST_PASSWORD,
            "personal_data_consent": True,
        }
        data.update(overrides)
        return data

    def test_registration_email_validation_and_case_insensitive_uniqueness(self):
        for invalid_email in (
            "abc",
            "abc@",
            "@mail.ru",
            "demo person@example.com",
        ):
            with self.subTest(email=invalid_email):
                form = RegistrationForm(
                    self.registration_data(email=invalid_email)
                )
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)

        valid_form = RegistrationForm(self.registration_data())
        self.assertTrue(valid_form.is_valid(), valid_form.errors)

        User.objects.create_user(
            username="email.owner",
            email="case@example.com",
            password=TEST_PASSWORD,
        )
        duplicate_form = RegistrationForm(
            self.registration_data(email="CASE@EXAMPLE.COM")
        )
        self.assertFalse(duplicate_form.is_valid())
        self.assertIn("email", duplicate_form.errors)

    def test_registration_code_activates_user_and_marks_email_verified(self):
        response = self.client.post(
            reverse("register"),
            self.registration_data(),
        )
        self.assertRedirects(response, reverse("verify_email"))
        registered = User.objects.get(username="demo.person")
        self.assertFalse(registered.is_active)
        self.assertEqual(len(mail.outbox), 1)

        session = self.client.session
        session["email_verification_code_hash"] = make_password("123456")
        session.save()
        response = self.client.post(reverse("verify_email"), {"code": "123456"})
        self.assertRedirects(response, reverse("login"))
        registered.refresh_from_db()
        self.assertTrue(registered.is_active)
        self.assertIsNotNone(registered.profile.email_verified_at)

    def test_registration_resend_respects_cooldown(self):
        response = self.client.post(
            reverse("register"),
            self.registration_data(username="resend.person"),
        )
        self.assertRedirects(response, reverse("verify_email"))
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.post(reverse("resend_email_verification"))
        self.assertRedirects(response, reverse("verify_email"))
        self.assertEqual(len(mail.outbox), 1)

        session = self.client.session
        session["email_verification_issued_at"] = int(
            (timezone.now() - timedelta(seconds=61)).timestamp()
        )
        session.save()
        response = self.client.post(reverse("resend_email_verification"))
        self.assertRedirects(response, reverse("verify_email"))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            mail.outbox[-1].subject,
            "Код подтверждения — Активный Сыктывкар",
        )

    @patch("accounts.services.send_mail", side_effect=SMTPException("temporary"))
    def test_registration_smtp_error_is_safe_and_rolls_back_user(self, _send_mail):
        response = self.client.post(
            reverse("register"),
            self.registration_data(username="smtp.failure"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Не удалось отправить письмо. Попробуйте ещё раз позже.",
        )
        self.assertFalse(User.objects.filter(username="smtp.failure").exists())
        self.assertNotIn("email_verification_user_id", self.client.session)

    def test_email_change_keeps_old_email_until_correct_code(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("change_email"),
            {
                "new_email": "new.address@example.com",
                "current_password": TEST_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("verify_email_change"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "existing@example.com")
        self.assertEqual(
            mail.outbox[0].subject,
            "Подтверждение нового адреса — Активный Сыктывкар",
        )

        session = self.client.session
        session["email_verification_code_hash"] = make_password("123456")
        session.save()
        response = self.client.post(
            reverse("verify_email_change"),
            {"code": "654321"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "existing@example.com")

        session = self.client.session
        session["email_verification_expires_at"] = 0
        session.save()
        response = self.client.post(
            reverse("verify_email_change"),
            {"code": "123456"},
        )
        self.assertContains(response, "Срок действия кода истёк")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "existing@example.com")

        session = self.client.session
        session["email_verification_expires_at"] = int(
            (timezone.now() + timedelta(minutes=10)).timestamp()
        )
        session.save()

        response = self.client.post(
            reverse("verify_email_change"),
            {"code": "123456"},
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new.address@example.com")
        self.assertIsNotNone(self.user.profile.email_verified_at)

    def test_email_change_rejects_bad_current_occupied_and_same_email(self):
        cases = (
            ("bad-email", TEST_PASSWORD),
            ("EXISTING@EXAMPLE.COM", TEST_PASSWORD),
            ("other@example.com", "wrong-password"),
        )
        for email, password in cases:
            with self.subTest(email=email):
                form = EmailChangeRequestForm(
                    {"new_email": email, "current_password": password},
                    user=self.user,
                )
                self.assertFalse(form.is_valid())

    @patch("accounts.services.send_mail", side_effect=SMTPException("temporary"))
    def test_email_change_smtp_error_keeps_current_email(self, _send_mail):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("change_email"),
            {
                "new_email": "new.smtp@example.com",
                "current_password": TEST_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Не удалось отправить письмо. Попробуйте ещё раз позже.",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "existing@example.com")
        self.assertNotIn("email_verification_pending_email", self.client.session)

    def test_old_email_notification_failure_does_not_break_email_change(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("change_email"),
            {
                "new_email": "new.notice@example.com",
                "current_password": TEST_PASSWORD,
            },
        )
        session = self.client.session
        session["email_verification_code_hash"] = make_password("123456")
        session.save()

        with patch(
            "accounts.views.send_mail",
            side_effect=SMTPException("temporary"),
        ):
            response = self.client.post(
                reverse("verify_email_change"),
                {"code": "123456"},
                follow=True,
            )

        self.assertContains(
            response,
            "Не удалось отправить письмо. Попробуйте ещё раз позже.",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new.notice@example.com")

    @patch(
        "django.contrib.auth.forms.PasswordResetForm.send_mail",
        side_effect=SMTPException("temporary"),
    )
    def test_password_reset_smtp_error_keeps_neutral_response(self, _send_mail):
        existing_response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )
        unknown_response = self.client.post(
            reverse("password_reset"),
            {"email": "unknown@example.com"},
        )

        self.assertEqual(existing_response.status_code, 302)
        self.assertEqual(unknown_response.status_code, 302)
        self.assertEqual(existing_response.url, reverse("password_reset_done"))
        self.assertEqual(unknown_response.url, reverse("password_reset_done"))

    def test_password_reset_uses_russian_project_email_and_is_neutral(self):
        existing_response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )
        unknown_response = self.client.post(
            reverse("password_reset"),
            {"email": "unknown@example.com"},
        )

        self.assertEqual(existing_response.status_code, 302)
        self.assertEqual(unknown_response.status_code, 302)
        self.assertEqual(existing_response.url, reverse("password_reset_done"))
        self.assertEqual(unknown_response.url, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "Восстановление пароля — Активный Сыктывкар",
        )
        self.assertIn("Активный Сыктывкар", mail.outbox[0].body)


class BlockingAndDeletionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="test.admin",
            email="admin@example.com",
            password=TEST_PASSWORD,
        )
        self.user = User.objects.create_user(
            username="blocked.person",
            email="blocked@example.com",
            first_name="Иван",
            last_name="Иванов",
            password=TEST_PASSWORD,
        )

    def test_temporary_block_login_message_unblock_and_expiry(self):
        self.assertTrue(
            self.client.login(username=self.user.username, password=TEST_PASSWORD)
        )
        self.client.logout()
        block_user(
            target=self.user,
            actor=self.admin,
            reason="Проверка блокировки",
            duration="1",
        )
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": TEST_PASSWORD},
        )
        self.assertContains(response, "временно заблокирован")
        self.assertNotIn("_auth_user_id", self.client.session)

        unblock_user(target=self.user, actor=self.admin)
        self.assertTrue(
            self.client.login(username=self.user.username, password=TEST_PASSWORD)
        )
        self.client.logout()

        block_user(
            target=self.user,
            actor=self.admin,
            reason="Проверка срока",
            duration="1",
        )
        self.user.profile.blocked_until = timezone.now() - timedelta(seconds=1)
        self.user.profile.save(update_fields=["blocked_until"])
        self.assertTrue(
            self.client.login(username=self.user.username, password=TEST_PASSWORD)
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_permanent_block_has_specific_message(self):
        block_user(
            target=self.user,
            actor=self.admin,
            reason="Бессрочная проверка",
            duration="permanent",
        )
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": TEST_PASSWORD},
        )
        self.assertContains(response, "Ваш аккаунт заблокирован")
        self.assertContains(response, "active.syktyvkar@mail.ru")

    def test_self_delete_anonymizes_and_preserves_published(self):
        category = Category.objects.create(name="Тестовая категория")
        published = Initiative.objects.create(
            title="Опубликованная",
            description="Описание",
            category=category,
            author=self.user,
            status="published",
        )
        draft = Initiative.objects.create(
            title="Черновик",
            description="Описание",
            category=category,
            author=self.user,
            status="draft",
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("delete_account"),
            {"current_password": TEST_PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

        self.user.refresh_from_db()
        published.refresh_from_db()
        draft.refresh_from_db()
        self.assertTrue(self.user.profile.is_deleted)
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.email, "")
        self.assertEqual(self.user.first_name, "")
        self.assertNotEqual(self.user.username, "blocked.person")
        self.assertEqual(published.author_id, self.user.pk)
        self.assertEqual(published.status, "published")
        self.assertTrue(draft.is_hidden)

        response = self.client.get(reverse("initiative_detail", args=[published.pk]))
        self.assertContains(response, "Удалённый пользователь")
        response = self.client.get(reverse("initiative_detail", args=[draft.pk]))
        self.assertRedirects(response, reverse("initiative_list"))
        self.assertFalse(
            self.client.login(username=self.user.username, password=TEST_PASSWORD)
        )

    def test_admin_soft_delete_uses_custom_safe_action(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("admin:auth_user_soft_delete", args=[self.user.pk])
        )
        self.assertContains(response, "Опубликованные инициативы пользователя будут сохранены")
        response = self.client.post(
            reverse("admin:auth_user_soft_delete", args=[self.user.pk])
        )
        self.assertRedirects(response, reverse("admin:auth_user_changelist"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile.is_deleted)
        self.assertTrue(
            AuditLog.objects.filter(
                user=self.admin,
                action__contains="Администратором удалён",
            ).exists()
        )

    def test_admin_block_and_unblock_views_require_reason_and_duration(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:auth_user_block", args=[self.user.pk]),
            {"reason": "Нарушение правил", "duration": "7"},
        )
        self.assertRedirects(
            response,
            reverse("admin:auth_user_change", args=[self.user.pk]),
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.user.profile.block_reason, "Нарушение правил")
        self.assertIsNotNone(self.user.profile.blocked_until)

        response = self.client.post(
            reverse("admin:auth_user_unblock", args=[self.user.pk])
        )
        self.assertRedirects(
            response,
            reverse("admin:auth_user_change", args=[self.user.pk]),
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.profile.block_reason, "")
