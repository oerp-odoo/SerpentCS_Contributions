# -*- coding: utf-8 -*-
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    over_credit = fields.Boolean("Allow Over Credit?")

    @api.multi
    def check_limit(self, no_raise=False):
        """Check if credit limit for partner was exceeded."""
        self.ensure_one()
        partner = self.partner_id
        moveline_obj = self.env['account.move.line']
        movelines = moveline_obj.\
            search([('partner_id', '=', partner.id),
                    ('account_id.user_type_id.type', 'in',
                    ['receivable', 'payable']),
                    ('full_reconcile_id', '=', False)])

        debit, credit = 0.0, 0.0
        today_dt = datetime.strftime(datetime.now().date(), DF)
        for line in movelines:
            if line.date_maturity < today_dt:
                credit += line.debit
                debit += line.credit

        if (credit - debit + self.amount_total) > partner.credit_limit:
            if not partner.over_credit and not self.over_credit:
                msg = 'Can not confirm Sale Order,Total mature due Amount ' \
                      '%s as on %s !\nCheck Partner Accounts or Credit ' \
                      'Limits !' % (credit - debit, today_dt)
                if no_raise:
                    return False
                raise UserError(_('Credit Over Limits !\n' + msg))
            else:
                # Do not adjust partner credit limit when just checking
                # before actually confirming sale order.
                if not no_raise:
                    partner.write({
                        'credit_limit': credit - debit + self.amount_total})
                return True
        else:
            return True

    @api.multi
    def action_confirm(self):
        """Extend to check credit limit before confirming sale order."""
        for order in self:
            order.check_limit()
        return super(SaleOrder, self).action_confirm()
