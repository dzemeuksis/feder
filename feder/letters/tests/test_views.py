import codecs
import json
import os
from datetime import datetime

from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm

from feder.alerts.models import Alert
from feder.cases.factories import CaseFactory
from feder.cases.models import Case
from feder.letters.models import Letter
from feder.letters.settings import LETTER_RECEIVE_SECRET
from feder.main.tests import PermissionStatusMixin
from feder.monitorings.factories import MonitoringFactory
from feder.records.models import Record
from feder.users.factories import UserFactory
from feder.virus_scan.factories import AttachmentRequestFactory

from ...es_search.tests import ESMixin
from ...virus_scan.models import Request as ScanRequest
from ..factories import (
    AttachmentFactory,
    IncomingLetterFactory,
    LetterFactory,
    OutgoingLetterFactory,
)


class ObjectMixin:
    def setUp(self):
        super().setUp()
        self.user = UserFactory(username="john")
        self.monitoring = self.permission_object = MonitoringFactory()
        self.case = CaseFactory(monitoring=self.monitoring)
        self.from_user = OutgoingLetterFactory(title="Wniosek", record__case=self.case)

        self.letter = self.from_institution = IncomingLetterFactory(
            title="Odpowiedz", record__case=self.case
        )


class LetterListViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:list")

    def test_hide_letter_from_quarantined_case(self):
        Case.objects.filter(pk=self.letter.case.pk).update(is_quarantined=True)
        response = self.client.get(self.get_url())
        self.assertNotContains(response, self.letter)

    def test_show_quarantined_letter_for_authorized(self):
        Case.objects.filter(pk=self.letter.case.pk).update(is_quarantined=True)
        self.grant_permission("monitorings.view_quarantined_case")
        self.login_permitted_user()
        response = self.client.get(self.get_url())
        self.assertContains(response, self.letter)

    def test_content(self):
        response = self.client.get(self.get_url())
        self.assertTemplateUsed(response, "letters/letter_filter.html")
        self.assertContains(response, "Odpowiedz")
        self.assertContains(response, "Wniosek")

    def test_show_previous_year_default(self):
        letter = LetterFactory()
        letter.created = letter.created.replace(year=2020)  # non-current year
        letter.save()
        response = self.client.get(self.get_url())
        self.assertNotContains(response, letter)


class LetterDetailViewTestCase(ESMixin, ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return self.letter.get_absolute_url()

    def test_content(self):
        response = self.client.get(self.get_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "letters/letter_detail.html")
        self.assertContains(response, self.letter.title)

    def test_show_note(self):
        response = self.client.get(self.get_url())
        self.assertContains(response, self.letter.note)

    def test_contains_link_to_report_spam(self):
        response = self.client.get(self.get_url())
        self.assertContains(response, _("Report spam"))
        self.assertContains(
            response, reverse("letters:spam", kwargs={"pk": self.letter.pk})
        )

    def test_contains_link_to_attachment(self):
        attachment = AttachmentFactory(letter=self.letter)
        self.assertNotContains(
            self.client.get(self.get_url()), attachment.get_absolute_url()
        )
        AttachmentRequestFactory(
            content_object=attachment,
            status=ScanRequest.STATUS.not_detected,
        )
        self.assertContains(
            self.client.get(self.get_url()), attachment.get_absolute_url()
        )

    def test_not_contain_link_to_similiar_on_disabled(self):
        similiar = IncomingLetterFactory(body=self.letter.body)
        self.index([similiar, self.letter])
        with self.settings(ELASTICSEARCH_SHOW_SIMILAR=False):
            response = self.client.get(self.get_url())
            self.assertNotContains(
                response,
                similiar.title,
                msg_prefix="Not found title of similiar letter",
            )
            self.assertNotContains(
                response,
                similiar.get_absolute_url(),
                msg_prefix="Not found link to similiar letter",
            )

    def test_contain_link_to_similiar_on_enabled(self):
        similiar = IncomingLetterFactory(body=self.letter.body)
        self.index([similiar, self.letter])
        with self.settings(ELASTICSEARCH_SHOW_SIMILAR=True):
            response = self.client.get(self.get_url())
            self.assertContains(
                response,
                similiar.title,
                msg_prefix="Not found title of similiar letter",
            )
            self.assertContains(
                response,
                similiar.get_absolute_url(),
                msg_prefix="Not found link to similiar letter",
            )


class LetterMessageXSendFileView(PermissionStatusMixin, TestCase):
    permission = []
    status_has_permission = 200
    status_anonymous = 200
    status_no_permission = 200

    def setUp(self):
        super().setUp()
        self.object = IncomingLetterFactory(is_spam=Letter.SPAM.non_spam)

    def get_url(self):
        return reverse("letters:download", kwargs={"pk": self.object.pk})

    # TODO hiding spam to be done by hiding download button in Letter view
    def test_deny_access_for_spam(self):
        spam_obj = IncomingLetterFactory(is_spam=Letter.SPAM.spam)
        url = reverse("letters:download", kwargs={"pk": spam_obj.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class LetterCreateViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.add_letter"]

    def get_url(self):
        return reverse("letters:create", kwargs={"case_pk": self.case.pk})


class LetterUpdateViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.change_letter"]

    def get_url(self):
        return reverse("letters:update", kwargs={"pk": self.from_user.pk})

    def test_update_case_number(self):
        self.login_permitted_user()
        new_case = CaseFactory()
        self.assertNotEqual(self.from_user.case, new_case)
        data = {
            "title": "Lorem",
            "body": "Lorem",
            "case": new_case.pk,
            "attachment_set-TOTAL_FORMS": 0,
            "attachment_set-INITIAL_FORMS": 0,
            "attachment_set-MAX_NUM_FORMS": 1,
        }
        resp = self.client.post(self.get_url(), data)
        self.assertEqual(resp.status_code, 302)
        self.from_user.refresh_from_db()
        self.from_user.record.refresh_from_db()
        self.assertEqual(self.from_user.case, new_case)


class LetterDeleteViewTestCase(ObjectMixin, PermissionStatusMixin, TransactionTestCase):
    permission = ["monitorings.delete_letter"]

    def get_url(self):
        return reverse("letters:delete", kwargs={"pk": self.from_user.pk})

    def test_remove_eml_file(self):
        self.login_permitted_user()
        self.assertTrue(os.path.isfile(self.from_user.eml.file.name))
        self.client.post(self.get_url())
        self.assertFalse(os.path.isfile(self.from_user.eml.file.name))

    def test_remove_letter_with_attachment(self):
        # TransactionTestCase has to be used to test file cleanup feature.
        self.login_permitted_user()
        attachment = AttachmentFactory(letter=self.from_user)
        self.assertTrue(os.path.isfile(attachment.attachment.file.name))
        self.client.post(self.get_url())
        self.assertFalse(os.path.isfile(attachment.attachment.file.name))


class LetterReplyViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.reply", "monitorings.add_draft"]

    def get_url(self):
        return reverse("letters:reply", kwargs={"pk": self.from_institution.pk})

    def test_send_reply(self):
        self.login_permitted_user()
        simple_file = SimpleUploadedFile(
            "file.mp4", b"file_content", content_type="video/mp4"
        )
        response = self.client.post(
            self.get_url(),
            {
                "html_body": "Lorem",
                "body": "Lorem",
                "title": "Lorem",
                "send": "yes",
                "attachment_set-TOTAL_FORMS": 1,
                "attachment_set-INITIAL_FORMS": 0,
                "attachment_set-MAX_NUM_FORMS": 1,
                "attachment_set-0-attachment": simple_file,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        new_letter = Letter.objects.filter(title="Lorem").get()
        new_attachment = new_letter.attachment_set.get()
        self.assertEqual(mail.outbox[0].attachments[0][0], new_attachment.filename)
        self.assertEqual(Record.objects.count(), 3)

    def test_no_send_drafts(self):
        self.login_permitted_user()
        response = self.client.post(
            self.get_url(),
            {
                "body": "Lorem",
                "title": "Lorem",
                "attachment_set-TOTAL_FORMS": 0,
                "attachment_set-INITIAL_FORMS": 0,
                "attachment_set-MAX_NUM_FORMS": 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


class LetterSendViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.reply"]

    def get_url(self):
        return reverse("letters:send", kwargs={"pk": self.from_user.pk})

    def test_send_reply(self):
        self.grant_permission()
        self.client.login(username="john", password="pass")
        response = self.client.post(self.get_url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        # reply to email should have organisation name
        self.assertTrue(
            self.monitoring.domain.organisation.name in mail.outbox[0].from_email
        )


class LetterFeedTestCaseMixin:
    def test_simple_render(self):
        resp = self.client.get(self.get_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.letter.title)


class LetterRssFeedTestCase(
    LetterFeedTestCaseMixin, ObjectMixin, PermissionStatusMixin, TestCase
):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:rss")


class LetterAtomFeedTestCase(
    LetterFeedTestCaseMixin, ObjectMixin, PermissionStatusMixin, TestCase
):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:atom")

    def test_item_enclosure_url(self):
        self.from_institution.eml.save("msg.eml", ContentFile("Foo"), save=True)
        resp = self.client.get(self.get_url())
        self.assertContains(resp, self.from_institution.eml.name)


class LetterMonitoringRssFeedTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:rss", kwargs={"monitoring_pk": self.monitoring.pk})


class LetterMonitoringAtomFeedTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:rss", kwargs={"monitoring_pk": self.monitoring.pk})


class LetterCaseRssFeedTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:rss", kwargs={"case_pk": self.case.pk})


class LetterCaseAtomFeedTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:atom", kwargs={"case_pk": self.case.pk})


class SitemapTestCase(ObjectMixin, TestCase):
    def test_letters(self):
        url = reverse("sitemaps", kwargs={"section": "letters"})
        needle = reverse("letters:details", kwargs={"pk": self.from_user.pk})
        response = self.client.get(url)
        self.assertContains(response, needle)


class LetterReportSpamViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    status_anonymous = 200
    status_no_permission = 200
    permission = []

    def get_url(self):
        return reverse("letters:spam", kwargs={"pk": self.from_institution.pk})

    def test_create_report_for_anonymous(self):
        response = self.client.post(self.get_url())
        self.assertEqual(Alert.objects.count(), 1)
        alert = Alert.objects.get()
        self.assertEqual(alert.link_object, self.from_institution)
        self.assertEqual(alert.author, None)

    def test_create_report_for_user(self):
        self.client.login(username="john", password="pass")
        response = self.client.post(self.get_url())
        self.assertEqual(Alert.objects.count(), 1)
        alert = Alert.objects.get()
        self.assertEqual(alert.link_object, self.from_institution)
        self.assertEqual(alert.author, self.user)


class LetterMarkSpamViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.spam_mark"]

    def get_url(self):
        return reverse("letters:mark_spam", kwargs={"pk": self.from_institution.pk})

    def test_hide_by_staff(self):
        self.login_permitted_user()
        response = self.client.post(self.get_url())
        self.from_institution = Letter.objects_with_spam.get(
            pk=self.from_institution.pk
        )
        self.assertEqual(self.from_institution.is_spam, Letter.SPAM.spam)

    def test_mark_as_valid(self):
        self.login_permitted_user()
        response = self.client.post(self.get_url(), data={"valid": "x"})
        self.from_institution.refresh_from_db()
        self.assertEqual(self.from_institution.is_spam, Letter.SPAM.non_spam)

    def test_accept_global_perms(self):
        user = UserFactory()
        assign_perm("monitorings.spam_mark", user)
        self.client.login(username=user.username, password="pass")

        response = self.client.post(self.get_url(), data={"valid": "x"})
        self.from_institution.refresh_from_db()
        self.assertEqual(self.from_institution.is_spam, Letter.SPAM.non_spam)


class MessageObjectMixin:
    def setUp(self):
        super().setUp()
        self.user = UserFactory(username="john")
        self.monitoring = MonitoringFactory()
        self.case = CaseFactory(monitoring=self.monitoring)


class UnrecognizedLetterListViewTestView(
    MessageObjectMixin, PermissionStatusMixin, TestCase
):
    permission = ["letters.recognize_letter"]
    permission_object = None

    def get_url(self):
        return reverse("letters:unrecognized_list")


class AssignLetterFormViewTestCase(MessageObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["letters.recognize_letter"]

    def setUp(self):
        super().setUp()
        self.user = UserFactory(username="john")
        self.msg = LetterFactory(record__case=None)

    def get_url(self):
        return reverse("letters:assign", kwargs={"pk": self.msg.pk})

    def test_assign_simple_letter(self):
        self.client.login(
            username=UserFactory(is_superuser=True).username, password="pass"
        )
        self.case = CaseFactory()
        response = self.client.post(self.get_url(), data={"case": self.case.pk})
        self.assertRedirects(response, reverse("letters:unrecognized_list"))
        self.assertTrue(self.case.record_set.exists())


class SpamAttachmentXSendFileViewTestCase(PermissionStatusMixin, TestCase):
    permission = []
    status_has_permission = 404
    status_anonymous = 404
    status_no_permission = 404
    spam_status = Letter.SPAM.spam

    def setUp(self):
        super().setUp()
        self.object = AttachmentFactory(letter__is_spam=self.spam_status)

    def get_url(self):
        return reverse(
            "letters:attachment", kwargs={"pk": self.object.pk, "letter_pk": 0}
        )


class StandardAttachmentXSendFileViewTestCase(PermissionStatusMixin, TestCase):
    permission = []
    status_has_permission = 200
    status_anonymous = 200
    status_no_permission = 200
    spam_status = Letter.SPAM.non_spam

    def setUp(self):
        super().setUp()
        self.object = AttachmentFactory(letter__is_spam=self.spam_status)

    def get_url(self):
        return reverse(
            "letters:attachment", kwargs={"pk": self.object.pk, "letter_pk": 0}
        )

    def test_forbid_access_for_infected(self):
        AttachmentRequestFactory(
            content_object=self.object, status=ScanRequest.STATUS.infected
        )
        self.login_permitted_user()
        resp = self.client.get(self.get_url())
        self.assertEqual(resp.status_code, 403)


class ReceiveEmailTestCase(TestCase):
    def setUp(self):
        self.url = reverse("letters:webhook")
        self.authenticated_url = f"{self.url}?secret={LETTER_RECEIVE_SECRET}"

    def test_required_autentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_add_to_case(self):
        case = CaseFactory()
        body = self._get_body(case)
        files = self._get_files(body)

        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")

        self.assertEqual(case.record_set.count(), 1)
        letter = case.record_set.all()[0].content_object
        self.assertEqual(
            letter.body, "W dniach 30.07-17.08.2018 r. przebywam na urlopie."
        )
        attachment = letter.attachment_set.all()[0]
        self.assertEqual(
            codecs.decode(letter.eml.read(), "zlib").decode("utf-8"), "12345"
        )
        self.assertEqual(attachment.attachment.read().decode("utf8"), "54321")

    def test_vacation_reply_type(self):
        case = CaseFactory()
        body = self._get_body(case, auto_reply_type="vacation-reply")
        files = self._get_files(body)

        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")
        self.assertEqual(
            case.record_set.all()[0].content_object.message_type,
            Letter.MESSAGE_TYPES.vacation_reply,
        )

    def test_disposition_notification_type(self):
        case = CaseFactory()
        body = self._get_body(case, auto_reply_type="disposition-notification")
        files = self._get_files(body)

        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")
        self.assertEqual(
            case.record_set.all()[0].content_object.message_type,
            Letter.MESSAGE_TYPES.disposition_notification,
        )

    def test_regular_type(self):
        case = CaseFactory()
        body = self._get_body(case, auto_reply_type=None)
        files = self._get_files(body)

        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")
        self.assertEqual(
            case.record_set.all()[0].content_object.message_type,
            Letter.MESSAGE_TYPES.regular,
        )

    def test_case_status(self):
        case = CaseFactory()

        # No letters yet
        self.assertFalse(case.confirmation_received)
        self.assertFalse(case.response_received)

        # Sending automatic response
        body = self._get_body(case, auto_reply_type="disposition-notification")
        files = self._get_files(body)
        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")
        case = Case.objects.get(id=case.id)
        self.assertTrue(case.confirmation_received)
        self.assertFalse(case.response_received)

        # Sending regular response
        body = self._get_body(case, auto_reply_type=None)
        files = self._get_files(body)
        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.json()["status"], "OK")
        case = Case.objects.get(id=case.id)
        self.assertTrue(case.confirmation_received)
        self.assertTrue(case.response_received)

    def test_no_match_of_case(self):
        body = self._get_body()
        files = self._get_files(body)

        self.assertEqual(Case.objects.count(), 0)

        response = self.client.post(path=self.authenticated_url, data=files)
        letter = Letter.objects.first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Case.objects.count(), 0)
        self.assertEqual(letter.case, None)

    def test_html_body(self):
        body = self._get_body(html_body=True)
        files = self._get_files(body)

        response = self.client.post(path=self.authenticated_url, data=files)
        letter = Letter.objects.first()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(letter.body)
        self.assertTrue(letter.html_body)

    def test_missing_version(self):
        body = self._get_body(html_body=True)
        del body["version"]
        files = self._get_files(body)
        response = self.client.post(path=self.authenticated_url, data=files)
        self.assertEqual(response.status_code, 400)

    def _get_files(self, body):
        files = MultiValueDict()
        files["manifest"] = SimpleUploadedFile(
            name="manifest.json",
            content=json.dumps(body).encode("utf-8"),
            content_type="application/json",
        )
        files["eml"] = SimpleUploadedFile(
            name="a9a7b32cdfa34a7f91c826ff9b3831bb.eml.gz",
            content=codecs.encode(b"12345", "zlib"),
            content_type="message/rfc822",
        )
        files["attachment"] = SimpleUploadedFile(name="my-doc.txt", content=b"54321")
        return files

    def _get_body(self, case=None, html_body=False, auto_reply_type="vacation-reply"):
        id_timer = str(datetime.now().time()).split(".")[1]
        body = {
            "headers": {
                "auto_reply_type": auto_reply_type,
                "cc": [],
                "date": "2018-07-30T11:33:22",
                "from": ["user-a@siecobywatelska.pl"],
                "message_id": f"<E1fk6QU-00CPTw-Ey-{id_timer}@s50.hekko.net.pl>",
                "subject": 'Odpowied\u017a automatyczna: "Re: Problem z dostarczeniem odp. na fedrowanie"',
                "to": [case.email if case else "user-b@example.com"],
                "to+": [
                    "user-b@siecobywatelska.pl",
                    "user-c@siecobywatelska.pl",
                    case.email if case else "user-b@example.com",
                ],
            },
            "version": "v2",
            "text": {
                # It's assumed that content is always given to webhook endpoint,
                # otherwise endpoint will generate exception.
                "content": "W dniach 30.07-17.08.2018 r. przebywam na urlopie.",
                "quote": "",
            },
            "files_count": 1,
            "files": [{"content": "MTIzNDU=", "filename": "my-doc.txt"}],
            "eml": {
                "filename": "a9a7b32cdfa34a7f91c826ff9b3831bb.eml.gz",
                "compressed": True,
            },
        }

        if html_body:
            body["text"][
                "html_content"
            ] = "<p>W dniach <i>30.07-17.08.2018 r.</i> przebywam na urlopie.</p>"
            body["text"]["html_quote"] = ""

        return body


class LetterResendViewTestCase(ObjectMixin, PermissionStatusMixin, TestCase):
    permission = ["monitorings.reply"]

    def get_url(self):
        return reverse("letters:resend", kwargs={"pk": self.from_user.pk})

    def test_forbid_resend_from_instituion(self):
        self.login_permitted_user()
        response = self.client.get(
            reverse("letters:resend", kwargs={"pk": self.from_institution.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_resend_create_new_letter(self):
        self.login_permitted_user()
        self.assertEqual(self.case.record_set.count(), 2)
        response = self.client.post(self.get_url(), data={})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.case.record_set.count(), 3)

        # verify content of letter
        letter = self.case.record_set.latest("pk").content_object
        self.assertNotEqual(letter.pk, self.from_user.pk)
        self.assertEqual(letter.title, self.from_user.title)
        self.assertEqual(letter.body, self.from_user.body)
        # verify content of mail
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            self.monitoring.domain.organisation.name in mail.outbox[0].from_email
        )
        self.assertTrue(self.case.institution.email in mail.outbox[0].to)
