import datetime

from mailpile.commands import Command
from mailpile.i18n import gettext as _
from mailpile.mailutils import Email
from mailpile.plugins.search import View
from mailpile.util import *


class SingleMessageView(View):

    @classmethod
    def view(cls, result):
        mid = result["message_ids"][0]
        return {"message": result["data"]["messages"][mid],
                "metadata": result["data"]["metadata"][mid]}


class PrintToFile(Command):
    """Print messages to HTML files"""

    def command(self):
        session, config, idx = self.session, self.session.config, self._idx()
        args = list(self.args)
        flags = []
        while args and args[0][:1] == '-':
            flags.append(args.pop(0))

        msg_idxs = list(self._choose_messages(args))
        if not msg_idxs:
            return self._error('No messages selected')

        wrote = []
        for msg_idx in msg_idxs:
            e = Email(idx, msg_idx)
            ts = long(e.get_msg_info(field=idx.MSG_DATE), 36)
            dt = datetime.datetime.fromtimestamp(ts)
            subject = e.get_msg_info(field=idx.MSG_SUBJECT)

            fn = ('%4.4d-%2.2d-%2.2d.%s.%s.html'
                  % (dt.year, dt.month, dt.day,
                     CleanText(subject,
                               banned=CleanText.NONDNS, replace='_'
                               ).clean.replace('____', '_')[:50],
                     e.msg_mid())
                  ).encode('ascii', 'ignore')

            session.ui.mark(_('Printing e-mail to %s') % fn)
            smv = SingleMessageView(session, arg=['=%s' % e.msg_mid()])
            html = smv.run().as_html()
            if '-sign' in flags:
                key = config.prefs.gpg_recipient
                html = '<printed ts=%d -->\n%s\n<!-- \n' % (time.time(), html)
                rc, signed = self._gnupg().sign(html.encode('utf-8'),
                                                fromkey=key,
                                                clearsign=True)
                if rc != 0:
                   return self._error('Failed to sign printout')
                html = '<!--\n%s\n-->\n' % signed.decode('utf-8')
            with open(fn, 'wb') as fd:
                fd.write(html.encode('utf-8'))
                wrote.append({'mid': e.msg_mid(), 'filename': fn})

        return self._success(_('Printed to %d files') % len(wrote), wrote)
