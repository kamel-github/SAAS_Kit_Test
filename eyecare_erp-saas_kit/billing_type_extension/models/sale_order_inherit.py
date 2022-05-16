from odoo import fields, models, api,_
from odoo.tools.float_utils import float_round as round
from odoo.http import request
from odoo.exceptions import Warning,UserError,ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'


    def _prepare_invoice(self):
        invoice_vals = super(SaleOrderInherit, self)._prepare_invoice()
        invoice_vals['billing'] = self.billing
        print("invoice valsssssssssssssssssssssssss\n",invoice_vals)
        # print(invoice_vals,'_________________________')
        return invoice_vals

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        # print('\n\n\nasdfsalkfdsfsfsdfsdfsd_____________________________', add_qty, set_qty, kwargs, product_id, line_id)
        self.ensure_one()
        product_context = dict(self.env.context)
        product_context.setdefault('lang', self.sudo().partner_id.lang)
        SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)
        # change lang to get correct name of attributes/values
        product_with_context = self.env['product.product'].with_context(product_context)
        product = product_with_context.browse(int(product_id))

        try:
            if add_qty:
                add_qty = int(add_qty)
        except ValueError:
            add_qty = 1

        try:
            if set_qty:
                set_qty = int(set_qty)
        except ValueError:
            set_qty = 0

        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))

        if line_id is not False:
            order_line = self._cart_find_product_line(product_id, line_id, **kwargs)[:1]

        # Create line if no line with product_id can be located
        if not order_line:
            if not product:
                raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
            received_no_variant_values = product.env['product.template.attribute.value'].browse([int(ptav['value']) for ptav in no_variant_attribute_values])
            received_combination = product.product_template_attribute_value_ids | received_no_variant_values
            product_template = product.product_tmpl_id

            # handle all cases where incorrect or incomplete data are received
            combination = product_template._get_closest_possible_combination(received_combination)

            # get or create (if dynamic) the correct variant
            product = product_template._create_product_variant(combination)

            if not product:
                raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

            product_id = product.id

            values = self._website_product_id_change(self.id, product_id, qty=1)

            # add no_variant attributes that were not received
            for ptav in combination.filtered(lambda ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values):
                no_variant_attribute_values.append({
                    'value': ptav.id,
                })

            # save no_variant attributes values
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            # add is_custom attribute values that were not received
            custom_values = kwargs.get('product_custom_attribute_values') or []
            received_custom_values = product.env['product.template.attribute.value'].browse([int(ptav['custom_product_template_attribute_value_id']) for ptav in custom_values])

            for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
                custom_values.append({
                    'custom_product_template_attribute_value_id': ptav.id,
                    'custom_value': '',
                })

            # save is_custom attributes values
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]

            # create the line
            # print("\n\ncreate_order_line____________ : ", values)
            order_line = SaleOrderLineSudo.create(values)


            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # ########################################################################
        # # Calculate values by including no of users in qty of sale order
        #
        config_path = self.env['ir.config_parameter'].sudo()
        config_user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        config_product = self.env['product.product'].sudo().search([('id', '=', int(config_user_product))])
        plan_users = config_path.search([('key', '=', 'plan_users')]).value

        # print('\n\n Order line ',order_line, order_line.order_id, order_line.product_id.id, config_product.id)
        config_product_flag = False
        if order_line.product_id.id == config_product.id:
            config_product_flag = True

        if order_line.order_id.billing == 'normal':
            if add_qty != None and order_line.order_id.saas_order:
                if not config_product_flag:
                    if order_line:
                        # print('llllllllllllllllllllllllllllllllllll', quantity, order_line.order_id.no_of_users)
                        quantity = quantity * order_line.order_id.no_of_users
                    elif order_line.order_id.no_of_users > 0 :
                            if product_id != config_product.id and order_line.product_uom_qty == 1:
                                # print('\n\n Order line2 ', order_line.order_id.no_of_users, order_line.product_uom_qty)
                                quantity = float(order_line.order_id.no_of_users) * order_line.product_uom_qty
        else:
            if product_id == config_product.id and  add_qty != None:
                # print('asdfsdfsad : ', quantity, order_line.product_uom_qty, '____________', plan_users)
                if quantity > 0 and not line_id:
                    quantity = abs(quantity - float(plan_users))
        # print("\n\nquantity : ", quantity)
        #######################################################################

        # Remove zero of negative lines
        if quantity <= 0:
            linked_line = order_line.linked_line_id
            order_line.unlink()
            if linked_line:
                # update description of the parent
                linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
        else:
            # update line
            no_variant_attributes_price_extra = [ptav.price_extra for ptav in order_line.product_no_variant_attribute_value_ids]
            values = self.with_context(no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra))._website_product_id_change(self.id, product_id, qty=quantity)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context.update({
                    'partner': order.partner_id,
                    'quantity': quantity * order_line.order_id.no_of_users if order_line.order_id.saas_order and config_product_flag == False and add_qty == None and order_line.order_id.no_of_users else quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                })

                product_with_context = self.env['product.product'].with_context(product_context, force_company=order.company_id.id) #.with_company(order.company_id.id)
                product = product_with_context.browse(product_id)

                values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    order_line._get_display_price(product),
                    order_line.product_id.taxes_id,
                    order_line.tax_id,
                    self.company_id
                )

            ########################################################################
            # Avoid Multiply user count for product manage users
            #
            if order_line.order_id.billing == 'normal':
                if add_qty != None and order_line.order_id.saas_order:
                    if order_line.product_id.id != config_product.id:
                        if order_line.order_id.no_of_users > 0:
                            values['product_uom_qty'] = quantity / order_line.order_id.no_of_users
                        # print('\n\n\njjjjjjjjjjjjjjjjjjj2', values)
            else:
                if add_qty != None and order_line.product_id.id == config_product.id:
                    # values['product_uom_qty'] = quantity + float(plan_users)
                    print('\n\n\njjjjjjjjjjjjjjjjjjj4', values)
            # ########################################################################

            order_line.write(values)
            # print('\n\n\njjjjjjjjjjjjjjjjjjj3', order_line.product_uom_qty, order_line.price_unit)

            # link a product to the sales order
            if kwargs.get('linked_line_id'):
                linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
                order_line.write({
                    'linked_line_id': linked_line.id,
                })
                linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
            # Generate the description with everything. This is done after
            # creating because the following related fields have to be set:
            # - product_no_variant_attribute_value_ids
            # - product_custom_attribute_value_ids
            # - linked_line_id
            order_line.name = order_line.get_sale_order_line_multiline_description_sale(product)

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)

        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """

        for line in self:
            # print('\n\n line.price_unit :',line.order_id, line.price_unit)
            order_id = line.order_id
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            users = line.order_id.no_of_users if order_id.billing == 'normal' else 1
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
                                            line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id,
                                            users=users)
            tax = (taxes['total_included'] - taxes['total_excluded'])

            if line.month:
                price_subtotal = taxes['total_excluded'] * line.month
                if line.month > 0 and line.order_id.no_of_users > 0:
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': price_subtotal + tax,
                        'price_subtotal': price_subtotal,
                    })


                else:
                    for line in self:
                        order = line.order_id
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        users = line.order_id.no_of_users if line.order_id.billing == 'normal' else 1
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
                                                        line.product_uom_qty,
                                                        product=line.product_id,
                                                        partner=line.order_id.partner_shipping_id,
                                                        users=users)
                        tax = (taxes['total_included'] - taxes['total_excluded'])
                        price_subtotal = taxes['total_excluded']
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': price_subtotal + tax,
                            'price_subtotal': price_subtotal,
                        })
                print("\nline             :",line)


#
# class AccountTax(models.Model):
#     _inherit = 'account.tax'
#     """Inherited to override tax calculation methode"""
#
#     def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None,
#                     is_refund=False,
#                     handle_price_include=True, users=1.0):
#         # print('Users____________________', users, quantity, price_unit)
#         if not self:
#             company = self.env.company
#         else:
#             company = self[0].company_id
#
#         taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)
#         base_excluded_flag = False  # price_include=False && include_base_amount=True
#         included_flag = False  # price_include=True
#         for tax in taxes:
#             if tax.price_include:
#                 included_flag = True
#             elif tax.include_base_amount:
#                 base_excluded_flag = True
#             if base_excluded_flag and included_flag:
#                 raise UserError(_(
#                     'Unable to mix any taxes being price included with taxes affecting the base amount but not included in price.'))
#
#         if not currency:
#             currency = company.currency_id
#         prec = currency.rounding
#
#         round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
#         if 'round' in self.env.context:
#             round_tax = bool(self.env.context['round'])
#
#         if not round_tax:
#             prec *= 1e-5
#
#         def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):
#
#             return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100
#
#         base = currency.round(price_unit * quantity * users)
#
#         sign = 1
#         if currency.is_zero(base):
#             sign = self._context.get('force_sign', 1)
#         elif base < 0:
#             sign = -1
#         if base < 0:
#             base = -base
#
#         total_included_checkpoints = {}
#         i = len(taxes) - 1
#         store_included_tax_total = True
#         # Keep track of the accumulated included fixed/percent amount.
#         incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
#         # Store the tax amounts we compute while searching for the total_excluded
#         cached_tax_amounts = {}
#         if handle_price_include:
#             for tax in reversed(taxes):
#                 tax_repartition_lines = (
#                         is_refund
#                         and tax.refund_repartition_line_ids
#                         or tax.invoice_repartition_line_ids
#                 ).filtered(lambda x: x.repartition_type == "tax")
#                 sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))
#
#                 if tax.include_base_amount:
#                     base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount)
#                     incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
#                     store_included_tax_total = True
#                 if tax.price_include or self._context.get('force_price_include'):
#                     if tax.amount_type == 'percent':
#                         incl_percent_amount += tax.amount * sum_repartition_factor
#                     elif tax.amount_type == 'division':
#                         incl_division_amount += tax.amount * sum_repartition_factor
#                     elif tax.amount_type == 'fixed':
#                         incl_fixed_amount += quantity * users * tax.amount * sum_repartition_factor
#                     else:
#                         # tax.amount_type == other (python)
#                         tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product,
#                                                          partner) * sum_repartition_factor
#                         incl_fixed_amount += tax_amount
#                         # Avoid unecessary re-computation
#                         cached_tax_amounts[i] = tax_amount
#                     # In case of a zero tax, do not store the base amount since the tax amount will
#                     # be zero anyway. Group and Python taxes have an amount of zero, so do not take
#                     # them into account.
#                     if store_included_tax_total and (
#                             tax.amount or tax.amount_type not in ("percent", "division", "fixed")
#                     ):
#                         total_included_checkpoints[i] = base
#                         store_included_tax_total = False
#                 i -= 1
#
#         total_excluded = currency.round(
#             recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))
#
#         base = total_included = total_void = total_excluded
#
#         taxes_vals = []
#         i = 0
#         cumulated_tax_included_amount = 0
#         for tax in taxes:
#             tax_repartition_lines = (
#                     is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(
#                 lambda x: x.repartition_type == 'tax')
#             sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))
#             price_include = self._context.get('force_price_include', tax.price_include)
#
#             # compute the tax_amount
#             if price_include and total_included_checkpoints.get(i):
#                 # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
#                 tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
#                 cumulated_tax_included_amount = 0
#             else:
#                 tax_amount = tax.with_context(force_price_include=False)._compute_amount(
#                     base, sign * price_unit, quantity, product, partner)
#
#             # Round the tax_amount multiplied by the computed repartition lines factor.
#             tax_amount = round(tax_amount, precision_rounding=prec)
#             factorized_tax_amount = round(tax_amount * sum_repartition_factor, precision_rounding=prec)
#
#             if price_include and not total_included_checkpoints.get(i):
#                 cumulated_tax_included_amount += factorized_tax_amount
#
#             # If the tax affects the base of subsequent taxes, its tax move lines must
#             # receive the base tags and tag_ids of these taxes, so that the tax report computes
#             # the right total
#             subsequent_taxes = self.env['account.tax']
#             subsequent_tags = self.env['account.account.tag']
#             if tax.include_base_amount:
#                 subsequent_taxes = taxes[i + 1:]
#                 subsequent_tags = subsequent_taxes.get_tax_tags(is_refund, 'base')
#
#             # Compute the tax line amounts by multiplying each factor with the tax amount.
#             # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
#             # amount. E.g:
#             #
#             # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
#             # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
#             # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
#             # in lines as 2 x 0.01.
#             repartition_line_amounts = [round(tax_amount * line.factor, precision_rounding=prec) for line in
#                                         tax_repartition_lines]
#             total_rounding_error = round(factorized_tax_amount - sum(repartition_line_amounts), precision_rounding=prec)
#             nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
#             rounding_error = round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
#                                    precision_rounding=prec)
#
#             for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):
#
#                 if nber_rounding_steps:
#                     line_amount += rounding_error
#                     nber_rounding_steps -= 1
#
#                 taxes_vals.append({
#                     'id': tax.id,
#                     'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
#                     'amount': sign * line_amount,
#                     'base': round(sign * base, precision_rounding=prec),
#                     'sequence': tax.sequence,
#                     'account_id': tax.cash_basis_transition_account_id.id if tax.tax_exigibility == 'on_payment' else repartition_line.account_id.id,
#                     'analytic': tax.analytic,
#                     'price_include': price_include,
#                     'tax_exigibility': tax.tax_exigibility,
#                     'tax_repartition_line_id': repartition_line.id,
#                     'group': groups_map.get(tax),
#                     'tag_ids': (repartition_line.tag_ids + subsequent_tags).ids,
#                     'tax_ids': subsequent_taxes.ids,
#                 })
#
#                 if not repartition_line.account_id:
#                     total_void += line_amount
#
#             # Affect subsequent taxes
#             if tax.include_base_amount:
#                 base += factorized_tax_amount
#
#             total_included += factorized_tax_amount
#             i += 1
#         return {
#             'base_tags': taxes.mapped(
#                 is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(
#                 lambda x: x.repartition_type == 'base').mapped('tag_ids').ids,
#             'taxes': taxes_vals,
#             'total_excluded': sign * total_excluded,
#             'total_included': sign * currency.round(total_included),
#             'total_void': sign * currency.round(total_void),
#         }
