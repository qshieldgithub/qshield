# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import time


class GenerateSaleOrderLine(models.Model):
    _name = 'generate.sale.order.line'
    _description = "Generate Sale Order line"

    sale_order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    service_type_consolidation_manual_ids = fields.One2many(comodel_name="service.type.consolidation.manual",
                                                            inverse_name="generate_sale_order_line_id",
                                                            string="Service Type consolidation")
    generate_service_type_variant_ids = fields.Many2many(comodel_name="generate.service.type.variant",
                                                         string="Service Type Variant")
    total_consolidation_price = fields.Float(string="Total Price")
    calculated_total_consolidation_price = fields.Float(compute="compute_calculated_total_consolidation_price",
                                                        store=True)

    # @api.onchange('total_consolidation_price')
    # def onchange_total_consolidation_price(self):
    #     print('-------------------------------------------------')
    #     if self.total_consolidation_price:
    #         self.total_consolidation_price = self.total_consolidation_price
    # self.sudo().update({'total_consolidation_price': self.calculated_total_consolidation_price})

    # def onchange_calculated_total_consolidation_price(self):
    #     self.total_consolidation_price = self.calculated_total_consolidation_price

    @api.depends('service_type_consolidation_manual_ids')
    def compute_calculated_total_consolidation_price(self):
        for rec in self:
            if rec.service_type_consolidation_manual_ids:
                rec.calculated_total_consolidation_price = sum(
                    rec.service_type_consolidation_manual_ids.mapped('price'))
                # rec.total_consolidation_price = rec.calculated_total_consolidation_price
            else:
                rec.calculated_total_consolidation_price = 0.0

    def update_consolidation_price(self):
        print('----------update_consolidation_price--------------------')
        service_type_consolidation_manual_ids = self.service_type_consolidation_manual_ids.filtered(
            lambda s: s.is_set_automatic == False)
        remaining_service_type_consolidation_manual_ids = self.service_type_consolidation_manual_ids - service_type_consolidation_manual_ids
        total_price = self.total_consolidation_price
        if self.total_consolidation_price > 0 and service_type_consolidation_manual_ids:
            for service_type_consolidation_manual_id in service_type_consolidation_manual_ids:
                service_type_consolidation_manual_id.sudo().write(
                    {'price': total_price / len(service_type_consolidation_manual_ids)})
        action = self.env.ref('qshield_crm.action_generate_sale_order_line').read()[0]
        action.update({'res_id': self.id})
        return action

    def generate_sale_order_line(self):
        print('------------------------')
        if self.generate_service_type_variant_ids:
            consolidation_list = []
            consolidation_ids = self.generate_service_type_variant_ids.mapped('variant_id').mapped('consolidation_id')
            for consolidation_id in consolidation_ids:
                variant_ids = self.generate_service_type_variant_ids.mapped('variant_id').filtered(
                    lambda s: s.consolidation_id == consolidation_id)
                generate_service_type_variant_list = []
                for generate_service_type_variant_id in self.generate_service_type_variant_ids:
                    product = generate_service_type_variant_id.variant_id.product_id
                    if product:
                        if generate_service_type_variant_id.variant_id in variant_ids:
                            generate_service_type_variant_list.append(generate_service_type_variant_id)
                service_type_consolidation_manual_id = self.service_type_consolidation_manual_ids.filtered(
                    lambda s: s.consolidation_id == consolidation_id)[0]
                consolidation_list.append({service_type_consolidation_manual_id: generate_service_type_variant_list})
            self.sale_order_id.order_line.sudo().unlink()
            for consolidation in consolidation_list:
                for key, values in consolidation.items():
                    self.sale_order_id.sudo().write({'order_line': [(0, 0, {
                        'display_type': 'line_section',
                        'name': key.consolidation_id.name + '                Price : ' + str(
                            key.price) + '             Quantity : ' + str(
                            key.quantity) + '   Total Price : ' + str(key.price * key.quantity),
                    })]})
                    price = 0
                    if key.price > 0 and len(values) > 0:
                        price = key.price / len(values)
                    for value in values:
                        self.sale_order_id.sudo().write({'order_line': [(0, 0, {
                            'product_id': value.variant_id.product_id.id,
                            # 'name': 'Variant :' + value.variant_id.name,
                            'product_uom_qty': value.quantity,
                            'price_unit': price
                        })]})
                print('--------------')

    def generate_service_variant(self):
        if not self.service_type_consolidation_manual_ids and self.generate_service_type_variant_ids:
            self.generate_service_type_variant_ids.sudo().unlink()
        if self.service_type_consolidation_manual_ids:
            consolidation_ids = self.service_type_consolidation_manual_ids.mapped('consolidation_id')
            generate_service_type_variant_without_consolidation = self.generate_service_type_variant_ids.filtered(
                lambda s: s.variant_id.consolidation_id not in consolidation_ids.ids)
            generate_service_type_variant_without_consolidation.sudo().unlink()
            for service_type_consolidation_manual_id in self.service_type_consolidation_manual_ids:
                price = 0.0
                if service_type_consolidation_manual_id.price:
                    price = service_type_consolidation_manual_id.price / len(
                        service_type_consolidation_manual_id.consolidation_id.service_type_variant_ids)
                for service_variant in service_type_consolidation_manual_id.consolidation_id.service_type_variant_ids:
                    generate_service_type_variant_id = self.env['generate.service.type.variant'].search(
                        [('variant_id', '=', service_variant.id)])
                    if not generate_service_type_variant_id:
                        variant_id = self.env['generate.service.type.variant'].create({
                            'variant_id': service_variant.id,
                            'price': price,
                            'quantity': service_type_consolidation_manual_id.quantity if service_type_consolidation_manual_id.quantity else 0.0
                        })
                        self.write({
                            'generate_service_type_variant_ids': [(4, variant_id.id)]
                        })
                    else:
                        generate_service_type_variant_id.write(
                            {'price': price,
                             'quantity': service_type_consolidation_manual_id.quantity if service_type_consolidation_manual_id.quantity else 0.0})
                        self.write({
                            'generate_service_type_variant_ids': [(4, generate_service_type_variant_id.id)]
                        })
        action = self.env.ref('qshield_crm.action_generate_sale_order_line').read()[0]
        action.update({'res_id': self.id})
        return action


class ServiceTypeConsolidationManual(models.Model):
    _name = 'service.type.consolidation.manual'
    _description = "Service Type Consolidation Manual"

    generate_sale_order_line_id = fields.Many2one('generate.sale.order.line')
    consolidation_id = fields.Many2one(comodel_name='ebs_mod.service.type.consolidation', string="Consolidation")
    price = fields.Float(string='Price')
    quantity = fields.Float(string='Quantity', default="1")
    is_set_automatic = fields.Boolean(string="Is set Automatic", default=False)

    @api.onchange('price')
    def onchange_price(self):
        if self._context.get('price'):
            self.is_set_automatic = True

class GenerateServiceTypeVariant(models.Model):
    _name = 'generate.service.type.variant'
    _description = "Service Type Consolidation Manual"
    _rec_name = 'variant_id'

    variant_id = fields.Many2one('ebs_mod.service.type.variants')
    price = fields.Float(string='Price')
    quantity = fields.Float(string='Quantity')
