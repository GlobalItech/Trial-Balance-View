# -*- coding: utf-8 -*-

from odoo import models, api, _
from datetime import datetime
# 
class report_account_coa(models.AbstractModel):
    _inherit = "account.coa.report"

    @api.model
    def _lines(self, line_id=None):
        lines = []
        context = self.env.context
        maxlevel = context['context_id'].hierarchy_3 and 3 or 1
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_accounts = {}
        period_number = 0
        initial_balances = {}
        context['periods'].reverse()
        total_debit_credit = []
        for period in context['periods']:
            total_debit_credit.append([0.0,0.0])
            res = self.with_context(date_from_aml=period[0], date_to=period[1], date_from=period[0] and company_id.compute_fiscalyear_dates(datetime.strptime(period[0], "%Y-%m-%d"))['date_from'] or None).group_by_account_id(line_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
            if period_number == 0:
                initial_balances = dict([(k, res[k]['initial_bal']['balance']) for k in res])
            for account in res:
                if account not in grouped_accounts.keys():
                    grouped_accounts[account] = [{'balance': 0, 'debit': 0, 'credit': 0} for p in context['periods']]
                grouped_accounts[account][period_number]['balance'] = res[account]['balance'] - res[account]['initial_bal']['balance']
            period_number += 1
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        title_index = ''
        total_initial_balance= 0
         
        for account in sorted_accounts:
            non_zero = False
            for p in xrange(len(context['periods'])):
                if not company_id.currency_id.is_zero(grouped_accounts[account][p]['balance']) or not company_id.currency_id.is_zero(initial_balances.get(account, 0)):
                    non_zero = True
            if not non_zero:
                continue
            for level in range(maxlevel):
                if (account.code[:level+1] > title_index[:level+1]):
                    title_index = account.code[:level+1]
                    total = map(lambda x: 0.00, xrange(len(context['periods'])))
                    if maxlevel>1:
                        for account_sum in sorted_accounts:
                            if account_sum.code[:level+1] == title_index:
                                for p in xrange(len(context['periods'])):
                                    total[p] += grouped_accounts[account_sum][p]['balance']
                            if account_sum.code[:level+1] > title_index:
                                break
                        total2 = ['']
                        for p in total:
                            total2.append(p >= 0 and self._format(p) or '')
                            total2.append(p < 0 and self._format(-p) or '')
                        total2.append('')
                    else:
                        total2 = [''] + ['' for p in xrange(len(context['periods']))]*2 + ['']
 
                    lines.append({
                        'id': title_index,
                        'type': 'line',
                        'name': level and title_index or (_("Class %s") % title_index),
                        'footnotes': {},
                        'columns': total2,
                        'level': level+1,
                        'unfoldable': False,
                        'unfolded': True,
                    })
            total_initial_balance += account in initial_balances and initial_balances[account] or 0.0
            p_number=0
            for p in xrange(len(context['periods'])):
                total_debit_credit[p_number][0] = total_debit_credit[p_number][0] + (grouped_accounts[account][p]['balance'] > 0 and grouped_accounts[account][p]['balance'] or 0.0)
                total_debit_credit[p_number][1] = total_debit_credit[p_number][1] + (grouped_accounts[account][p]['balance'] < 0 and -grouped_accounts[account][p]['balance'] or 0.0)
                p_number+=1
                
            
            lines.append({
                'id': account.id,
                'type': 'account_id',
                'name': account.code + " " + account.name,
                'footnotes': self.env.context['context_id']._get_footnotes('account_id', account.id),
                'columns': [account in initial_balances and self._format(initial_balances[account]) or self._format(0.0)] +
                            sum([[grouped_accounts[account][p]['balance'] > 0 and self._format(grouped_accounts[account][p]['balance']) or '',
                                 grouped_accounts[account][p]['balance'] < 0 and self._format(-grouped_accounts[account][p]['balance']) or '']
                                for p in xrange(len(context['periods']))], []),
                'level': 1,
                'unfoldable': False,
            })
        if lines:
            total_debit_credit = sum(total_debit_credit,[])
            total_debit_credit = map(lambda x:self._format(x),total_debit_credit)
            total_columns = [self._format(total_initial_balance)] + total_debit_credit
            lines.append({
                        'id': eval(title_index)+1,
                        'type': 'total',
                        'name': _('Total'),
                        'footnotes': {},
                        'columns': total_columns,
                        'level': level+1,
                        'unfoldable': False,
                        'unfolded': True,
                    })
        return lines


class account_context_coa(models.TransientModel):
    _inherit = "account.context.coa"

    def get_columns_names(self):
        columns = [_('Initial Balance')]
        if self.comparison and (self.periods_number == 1 or self.date_filter_cmp == 'custom'):
            columns += [_('Debit'), _('Credit')]
        elif self.comparison:
            for period in self.get_cmp_periods(display=True):
                columns += [_('Debit'), _('Credit')]
        return columns + [_('Debit'), _('Credit')]

