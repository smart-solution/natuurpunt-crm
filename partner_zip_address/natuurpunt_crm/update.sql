update res_partner set crab_used = false where street_id IS NULL;

update res_partner set email = email_website where email = '' and not(email_website = '');

update membership_membership_line set date_to = '2013-11-30' where date_to IS NULL;

update res_partner set free_member = false;
update res_partner set free_member = true from membership_membership_line where partner = res_partner.id and membership_id = 3;

update res_partner set membership_state = 'paid' where membership_state IS NULL;
update res_partner set membership_state = 'canceled' from membership_membership_line
where membership_state = 'paid'
  and partner = res_partner.id
  and membership_membership_line.date_cancel < '2013-11-30';
update res_partner set membership_state = 'old' from membership_membership_line
where membership_state = 'paid'
  and partner = res_partner.id
  and membership_membership_line.date_to < '2013-11-30';

update res_partner set membership_start = date_from, membership_stop = date_to, membership_cancel = date_cancel from membership_membership_line
where partner = res_partner.id;

update res_partner set membership_state = NULL where membership_start IS NULL and membership_stop IS NULL;

update res_partner
set department_id = partner_id 
from res_organisation_city_rel
where res_partner.zip_id = res_organisation_city_rel.zip_id;
