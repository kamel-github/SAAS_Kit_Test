odoo.define('saas_product.website',
	function(require) {
		"use strict";
		var ajax = require('web.ajax');
		var selected_term = 'from_first_date'
		var type = 'new'
		var is_package_count = 0;   // Updated for pacakge product
//        var SeoConfigurator1 = require("website.seo")



		$(".maindiv").mouseover(function(){
			$('.maindiv').addClass('animate1');
		});
		
		$(document).ready(function() {
            gettopupflagfromsetting();

            function gettopupflagfromsetting(){
                $.ajax({
                    url : '/shop/getDefaultTopupFlag',
                    async : false,
                    data : { },
                    success : function(data) {
                        var res = JSON.parse(data);
                        if(res.hide_topup){
                            $('#topup').hide();
                            $('#topup_text').hide();
                        }else{
                            $('#topup').show();
                            $('#topup_text').show();
                        }
                    }
                })
            }

			//To restrict Underscore in Database name
			$('.input-div-db').keypress(function(key) {
		        if(key.charCode == 95) return false;
		    });

				
			$("#address_next_btn").click(function(){
				$('#address_form').submit();
			});

			$('#selection_payment select[name="payment_mt"]').on('change', function () {
			var payment_value=$(this).val();
				if (payment_value == 'no_option')
				{
				    alert("Please Select valid option")
				}
				else
				{
				    ajax.jsonRpc('/check/payment/method', 'call', {'payment_value':payment_value})
                            .then(function (result) {

                            if ('tenant_topup' in result)
                            {

                                if(result.tenant_topup ==  false)
                                {
                                    alert("Your Trial Period Is Expired proceed further please select 'pay now'")
                                    window.location.replace("/shop/payment");
                                }

                            }

                            if ('state' in result)
                            {
                                if (result.state <= 0)
                                {
                                    if ('tenant_topup' in result)
                                    {

                                    if(result.tenant_topup ==  true)
                                    {
                                        alert("You cannot choose trial period proceed further please select 'pay now'");
//                                    ("#payement_base").val('no_option')
                                        document.getElementById("payement_base").value = "no_option";
                                        window.location.replace("/shop/payment");
                                    }

                                    }
                                    else{
                                    alert("You cannot choose trial period proceed further please select 'pay now'");
//                                    ("#payement_base").val('no_option')
                                    document.getElementById("payement_base").value = "no_option";
                                    window.location.replace("/shop/payment");
                                    }
                                }
                                else
                                {
                                    window.location.replace("/shop/payment");
//                                    document.getElementById("payement_base").selectedIndex = "3";
//                                    console.log("rrrrrrrrrrrrrrrrr233")
//                                    document.getElementById("payement_base").value = "True";
                                }

                            }
                            else{
                                window.location.replace("/shop/payment");
//                                document.getElementById("payement_base").selectedIndex = "2";
//                                console.log("rrrrrrrrrrrrrrrrr23")
//                                document.getElementById("payement_base").value = "True";
                            }

                            });
                }
			});


			var webUrl = window.location.pathname
//            console.log('Web url )))))))))))))))))))))))))))))) : ', webUrl)
			if(webUrl.includes('/shop/payment')){
                $.ajax({
                    url: '/get_applicant_details',
                    data: {},
                    success: function(data)
                    {
                        var result = JSON.parse(data);
                        if(result){
                            $("#payement_base").val(result['select_payment_option'])
                        }
                    }
                });
            }


			 if(webUrl.includes('/shop/confirmation')){
//                         $(function () {
//                        var msg = _t("We are Creating your Database, please wait ...");
//                        $.blockUI({
//                            'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
//                                '    <br />' + msg +
//                                '</h2>'
//                        });
//                        });
                    console.log('Inside shop payment confirmation');
                    window.location.replace("/shop/order_confirm");
                }
			
			
			if (document.getElementsByClassName('.product_check')) {
				var checkboxes = document.getElementsByClassName('product_check');
				for (var i = 0; i < checkboxes.length; i++) {
					checkboxes[i].checked = false;
				}
			}
			
			if($('#products_calc')){
				$('#top_up_instance_calculation').hide();
			}

			if ($('input[type=radio]')) {
				$("#topup_instance").hide();
				$('#topup').on('click', function() {
					
					$("#topup_instance").show();
					$("#new_instance").hide();
					$('#top_up_instance_calculation').show();
					$('#new_instance_calculation').hide();
					type='topup';

                    // Updated for is package product
                    is_package_count = 0;
				    $('.product_check').prop('checked', false)
                    $('.package').hide();
                    document.getElementById('topup_apps').innerHTML = '0 Apps';
                    document.getElementById('topup_apps_price').innerHTML = '0.00' ;
                    document.getElementById('topup_all_total').innerHTML = '0.00';
				    /////////////////////////////////////////////////////////////////
				})

				$('#new').on('click', function() {

                    // Updated for is package product
                    is_package_count = 0;
				    $('.package').show();
                    $('.product_check').prop('checked', false)
                    document.getElementById('m_num_apps').innerHTML = '0 Apps';
                    document.getElementById('num_apps').innerHTML = '0 Apps';
                    document.getElementById('apps_price').innerHTML = '0.00';
                    document.getElementById('all_total').innerHTML = '0.00';
                    document.getElementById('m_apps_price').innerHTML = '0.00';
                    document.getElementById('m_all_total').innerHTML = '0.00';
					console.log(is_package_count);

                    if(is_package_count > 1){
                        alert('Sorry ! You can not purchase two or more packages in one Order. You may select additional individual products instead.')
                        return false;
                    }
                    ////////////////////////////////////////////////////

					$("#topup_instance").hide();
					$("#new_instance").show();
					$('#top_up_instance_calculation').hide();
					$('#new_instance_calculation').show();
					type='new';

				})
			}

			$("#instance").keypress(function(e) {
				var chr = String.fromCharCode(e.which);
				if ("abcdefghijklmnopqrstuvwxyz1234567890_".indexOf(chr) < 0)
					return false;
			});
		})
						
		$(function(){
			$('#db_option').on('change',function(){
				
				var num_users = document.getElementById('topup_users');

				var dbusers = document.getElementById('db_option');
				var nu = dbusers.options[dbusers.selectedIndex];
				var usersnum = parseInt(nu.getAttribute('usersnumber'));
				var dbterm = nu.getAttribute('dbterm');
				
				var all_total = document.getElementById('topup_all_total');
				var year_all_total = document.getElementById('all_total');
				var m_all_total = document.getElementById('m_all_total');
				
				var topup_apps = document.getElementById('topup_apps');
				var num_apps = document.getElementById('num_apps');
				var m_num_apps = document.getElementById('m_num_apps');
				
				var t_apps_price = document.getElementById('topup_apps_price');
				var apps_price = document.getElementById('apps_price');
				var m_apps_price = document.getElementById('m_apps_price');
				
//				var a_p = apps_price.innerHTML;
				
				var checkboxes = document.getElementsByClassName('product_check');
				for (var i = 0; i < checkboxes.length; i++) {
					checkboxes[i].checked = false;
				}
				
				t_apps_price.innerHTML = '0.00';
				apps_price.innerHTML = '0.00';
				m_apps_price.innerHTML = '0.00';
				
				topup_apps.innerHTML = '0 Apps';
				num_apps.innerHTML = '0 Apps';
				m_num_apps.innerHTML = '0 Apps';
				
				num_users.innerHTML = usersnum;
				
				all_total.innerHTML = '0.00';
				year_all_total.innerHTML = '0.00';
				m_all_total.innerHTML = '0.00';
				
//				all_total.innerHTML = (parseFloat(a_p) * parseFloat(num_users.innerHTML)).toFixed(2);
				
				if (dbterm == 1){
					selected_term = 'from_first_date';
				}
				if (dbterm == 4){
					selected_term = 'year';
//					all_total.innerHTML = ((parseFloat(a_p) * 12) * parseFloat(num_users.innerHTML)).toFixed(2);
				}
				
			})
		})

		$(function() {
			$('#users').on('change',function() {
                var num_users = document.getElementById('num_users');
			    var dy_users = document.getElementById('users').value;
				var m_num_users = document.getElementById('m_num_users');
				var all_total = document.getElementById('all_total');
				var m_all_total = document.getElementById('m_all_total');
				var apps_price = document.getElementById('apps_price');
				var m_apps_price = document.getElementById('m_apps_price');

				var a_p = apps_price.innerHTML;
				var m_a_p = m_apps_price.innerHTML;

				num_users.innerHTML = dy_users;
				m_num_users.innerHTML = dy_users;

				var n_u = parseFloat(num_users.innerHTML)
				var m_n_u = parseFloat(m_num_users.innerHTML)

				all_total.innerHTML = (n_u * parseFloat(a_p))
						.toFixed(2);
				m_all_total.innerHTML = (m_n_u * parseFloat(m_a_p))
						.toFixed(2);

                console.log('Parent');

			})
		});

		$(function() {
			$(document.getElementsByClassName('product_check'))
				.on('change',function() {

                    /////////////////////////////////////////////// Updated for is package product
					var pro_chk = document.getElementById(this.id);
					    var is_package = pro_chk.getAttribute('is_package')
                    if(is_package == "True"){
                        (pro_chk.checked == true)? is_package_count += 1 : is_package_count -= 1 ;
                        if((type == 'new')&&(is_package_count > 1   )){
                            alert('Sorry ! You can not purchase two or more packages in one Order. You may select additional individual products instead.')
                            pro_chk.checked = false;
                            is_package_count -= 1;
                            return false;
                        }
                    }
//                   console.log(is_package+" -> Package product Count : "+is_package_count)
                   ///////////////////////////////////////////////////

					var dbusers = document.getElementById('db_option');
					var nu = ''
					var dbterm = ''
					if (dbusers == null){
						nu = 1;
						dbterm = 4; 
					}
					else
					{
						nu = dbusers.options[dbusers.selectedIndex];
						dbterm = nu.getAttribute('dbterm');
					}
					
					var usersnum = document.getElementById('topup_users');
					var num_users = document.getElementById('num_users');
					var m_num_users = document.getElementById('m_num_users');
					
					var topup_apps = document.getElementById('topup_apps');
					var num_apps = document.getElementById('num_apps');
					var m_num_apps = document.getElementById('m_num_apps');

					var apps_price = document.getElementById('apps_price');
					var m_apps_price = document.getElementById('m_apps_price');
					var topup_apps_price = document.getElementById('topup_apps_price');
					
//					var pro_chk = document.getElementById(this.id);
					var all_total = document.getElementById('all_total');
					var m_all_total = document.getElementById('m_all_total');
					var topup_all_total = document.getElementById('topup_all_total');
					
					var pro_price = pro_chk.getAttribute('pro_price');

					var a_p = apps_price.innerHTML;
					var m_a_p = m_apps_price.innerHTML;
					var t_a_p = topup_apps_price.innerHTML;
					
					var n_a = num_apps.innerHTML;

					var total = all_total.innerHTML;
					var m_total = m_all_total.innerHTML;
					var t_total = topup_all_total.innerHTML;
					
					var n_u = parseFloat(num_users.innerHTML)
					var m_n_u = parseFloat(m_num_users.innerHTML)
					var u_n = parseFloat(topup_users.innerHTML)
					
					var apps = '';

//					while (n_a.charAt(0) == ' '
//							|| n_a.charAt(0) == '\t'
//							|| n_a.charAt(0) == '\n') {
//						n_a = n_a.substr(1);
//					}


//					while (n_a.charAt(0) != ' ') {
//
//					     if (n_a.charAt(1) == 0)
//					        {
//					          console.log("XXXXXXXXXXXXXXXXXXXXXXXXXXXX",n_a)
//					          apps=n_a + n_a.charAt(1)
//					          console.log("mmmmmmmmmmmmmmmmmmmmmmmmmmmmm",apps)
//					        }
//						apps = n_a.charAt(0);
//						console.log("apps::::::::::::::::::::::::",apps)
//						n_a = n_a.substr(1);
//
//
//
//					}
                    var checkboxes = document.getElementsByClassName('product_check');
                    var j=-1;
                    var k=1;
                    for (var i = 0; i < checkboxes.length; i++) {
							if (checkboxes[i].checked) {
								j=j+1;

							}
						}




					apps = parseInt(j);
					total = parseFloat(total);
					m_total = parseFloat(m_total);

					if (pro_chk.checked == true) {
						apps_price.innerHTML = (parseFloat(a_p) + parseFloat(pro_price * 12)).toFixed(2);
						m_apps_price.innerHTML = (parseFloat(m_a_p) + parseFloat(pro_price)).toFixed(2);
						num_apps.innerHTML = (apps + 1) + ' Apps';
						m_num_apps.innerHTML = (apps + 1) + ' Apps';
						topup_apps.innerHTML = (apps + 1) + ' Apps';
						
						all_total.innerHTML = (total + parseFloat(pro_price * 12 * n_u)).toFixed(2);
						m_all_total.innerHTML = (m_total + parseFloat(pro_price * m_n_u)).toFixed(2);
						
						if (dbterm == 1){
							topup_apps_price.innerHTML = (parseFloat(t_a_p) + parseFloat(pro_price)).toFixed(2);
							topup_all_total.innerHTML = (parseFloat(t_total) + parseFloat(pro_price * u_n)).toFixed(2);
						}
						if (dbterm == 4){
							topup_apps_price.innerHTML = (parseFloat(t_a_p) + parseFloat(pro_price * 12)).toFixed(2);
							topup_all_total.innerHTML = (parseFloat(t_total) + parseFloat(pro_price * 12 * u_n)).toFixed(2);
						}
					}

					if (pro_chk.checked == false && (parseFloat(a_p) > 0 || parseFloat(t_a_p) > 0)) {
						apps_price.innerHTML = (parseFloat(a_p) - parseFloat(pro_price * 12)).toFixed(2);
						m_apps_price.innerHTML = (parseFloat(m_a_p) - parseFloat(pro_price)).toFixed(2);
						k=j+2
						num_apps.innerHTML = (k - 1) + ' Apps';
						m_num_apps.innerHTML = (k - 1) + ' Apps';
						topup_apps.innerHTML = (k - 1) + ' Apps';
						
						all_total.innerHTML = (total - parseFloat(pro_price * 12 * n_u)).toFixed(2);
						m_all_total.innerHTML = (m_total - parseFloat(pro_price * m_n_u)).toFixed(2);
						
						if (dbterm == 1){
							topup_apps_price.innerHTML = (parseFloat(t_a_p) - parseFloat(pro_price)).toFixed(2);
							topup_all_total.innerHTML = (parseFloat(t_total) - parseFloat(pro_price * u_n)).toFixed(2);
						}
						if (dbterm == 4){
							topup_apps_price.innerHTML = (parseFloat(t_a_p) - parseFloat(pro_price * 12)).toFixed(2);
							topup_all_total.innerHTML = (parseFloat(t_total) - parseFloat(pro_price * 12 * u_n)).toFixed(2);
						}
					}

				})
		});

		$(function() {
			$(document.getElementById('year')).on('click',
					function() {
						selected_term = 'year'
					})
		})
		$(function() {
			$(document.getElementById('month')).on('click',
					function() {
						selected_term = 'from_first_date'
					})
		})
		$(function() {
			$('#pay').on('click',function() {
			    var ret = true
				var dbusers = document.getElementById('db_option')
				var nu = ''
				if (dbusers != null)
				{
					nu = dbusers.options[dbusers.selectedIndex];
				}
				if(nu == ''  && $("input:radio[name='type']:checked").val() == 'topup'){
					alert("No Tenant Selected , Please Create a New Instance");
				}
				else{
					if (type == "new") {
						var dy_users = document
								.getElementById('users').value;
						var dbname = document
								.getElementById('instance').value;
						var checkboxes = document
								.getElementsByClassName('product_check');
						var ids = "";

						if (dbname == ''){
							$('#instance').css({
								'border-color' : 'red'
							})
							alert("Please Provide Instance Name")
							return false
						}
						else{
							$('#instance').css({
								'border-color' : '#2D81B3'
							})
						}
						
						if (dbname.match(/^\d/)) {
							$('#instance').css({
								'border-color' : 'red'
							})
							alert("Instance Name should not start with Digits!")
							return false
							}
						else{
							$('#instance').css({
								'border-color' : '#2D81B3'
							})
						}
							
						
						
//						if(parseInt($('#all_total').text()) < 1){
//							alert("please select atleast one product!")
//							return false
//						}
						
						for (var i = 0; i < checkboxes.length; i++) {
							if (checkboxes[i].checked) {
								if (ids.length < 1) {
									ids = checkboxes[i].getAttribute('pro_id');
								} else {
									ids = ids + "," + checkboxes[i].getAttribute('pro_id');
								}
							}
						}

						var language = document.getElementById('language').value;
                        if(!language){
                            alert('Please Select Language');
                            return false
                        }

						$.ajax({
								url : '/shop/checkout2buy',
								async : false,
								data : {
									term : selected_term,
									ids : ids,
									dbname : dbname,
									num : dy_users,
									new_instance: true,
									language : language,
								},
								success : function(data) {
									var data1 = JSON.parse(data)
									if (data1.exist == true){
										alert("Instance name is not available")
										ret = false
									}
									else{
										$("#tosubmit").submit();
									}
								}
							})
					}
					if (type == "topup"){
//						$( "#db_option" ).val();
						var checkboxes = document
						.getElementsByClassName('product_check');
						var ids = "";
						for (var i = 0; i < checkboxes.length; i++) {
							if (checkboxes[i].checked) {
								if (checkboxes[i].checked) {
									if (ids.length < 1) {
										ids = checkboxes[i].getAttribute('pro_id');
									} else {
										ids = ids + "," + checkboxes[i].getAttribute('pro_id');
									}
								}
							}
						}
						$.ajax({
									url : '/shop/checkout2topup',
									async : false,
									data : {
										ids : ids,
										db_id : $( "#db_option" ).val(),
										new_instance: false,
									},
									success : function(data) {
										$("#tosubmit").submit();
										}
									})
						}
					}
				
				
				return ret
				})

	});
	$('#o_payment_form_pay').on('click', function () {
	       var webUrl = window.location.pathname
            console.log('Web url )))))))))))))))))))))))))))))) : ', webUrl)
			if(webUrl.includes('/shop/payment')){
//                    for passing payment option
                    var payment_value = $('#selection_payment select[name="payment_mt"]').val()
                    console.log("paymentsssssss",payment_value)
                    var pay_term = sessionStorage.getItem('selected_term');
                    var space_product = sessionStorage.getItem('space_product');
//                    console.log("spaceeeeeeeeee",space_product);
                    $.ajax({
                            url: '/get_applicant_details1',
                            data: {
                            space_product,space_product,
                            free_trial: payment_value },
                            success: function(data)
                            {
                            sessionStorage.setItem('space_product', "no");
                            var result = JSON.parse(data);
                            console.log(result.db_false)
                            if(result.db_false == true)
                            {
                                sessionStorage.setItem('space_product', "no");
                                window.location.replace("/shop/payment")
                                alert("Warning ! Something went wrong. We experience some issue while processing your order. Please try after some time." );

                            }
                            else
                            {
                                sessionStorage.setItem('space_product', "no");
                                console.log("Sucessfull topup")
                            }
                            }
                            });


                    }
	})




//SeoConfigurator1.SeoConfigurator.include({
//    start: function () {
//        var self = this;
//
//        this.$modal.addClass('oe_seo_configuration');
//
//        this.htmlPage = new HtmlPage();
//
//        this.disableUnsavableFields().then(function () {
//            // Image selector
//            self.metaImageSelector = new MetaImageSelector(self, {
//                htmlpage: self.htmlPage,
//                title: self.htmlPage.getOgMeta().metaTitle,
//                metaImg : self.metaImg || self.htmlPage.getOgMeta().ogImageUrl,
//                pageImages : _.pluck(self.htmlPage.images().get(), 'src'),
//                previewDescription: _t('The description will be generated by social media based on page content unless you specify one.'),
//            });
//
//            console.log(self.metaImageSelector.customImgUrl, "________________URL1")
//            self.metaImageSelector.appendTo(self.$('.js_seo_image'));
//
//            // title and description
//            self.metaTitleDescription = new MetaTitleDescription(self, {
//                htmlPage: self.htmlPage,
//                canEditTitle: self.canEditTitle,
//                canEditDescription: self.canEditDescription,
//                isIndexed: self.isIndexed,
//                previewDescription: _t('The description will be generated by search engines based on page content unless you specify one.'),
//            });
//            self.metaTitleDescription.on('title-changed', self, self.titleChanged);
//            self.metaTitleDescription.on('description-changed', self, self.descriptionChanged);
//            self.metaTitleDescription.appendTo(self.$('.js_seo_meta_title_description'));
//
//            // keywords
//            self.metaKeywords = new MetaKeywords(self, {htmlPage: self.htmlPage});
//            self.metaKeywords.appendTo(self.$('.js_seo_meta_keywords'));
//        });
//    },
//});

});
