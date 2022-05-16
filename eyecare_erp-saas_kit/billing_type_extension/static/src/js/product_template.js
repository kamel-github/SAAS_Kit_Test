odoo.define('billing_type_extension.website',
	function(require) {
		"use strict";
		var ajax = require('web.ajax');
		var selected_term = 'from_first_date'
		var type = 'new'
        var invoicing_policy = 'normal'
        var plan_users = 1
        var is_package_count = 0;   // Updated for pacakge product


        $(function(){
            $('#users').off('change');
            $('.product_check').off('change');

            getBillingTypeFromResConfig();

            function getBillingTypeFromResConfig(){
                 $.ajax({
                    url : '/shop/getDefaultBillingType',
                    async : false,
                    data : { },
                    success : function(data) {
                        var res = JSON.parse(data);
                        console.log(res.billing_type+'___________'+"price");
                        invoicing_policy = res.billing_type
                    }
                })
            }

            getPlanUsers();

            function getPlanUsers(){
                if(invoicing_policy == 'user_plan_price'){
                    $('.pricing-rules').hide();
                    $('#second_billing_type').show();

                    $('#m_extra_users_row').show();
                    $('#y_extra_users_row').show();

                    $.ajax({
                        url : '/shop/get_default_plan_users',
                        async : false,
                        data : {
                            val : invoicing_policy,
                        },
                        success : function(data) {
                            var res = JSON.parse(data);
                            console.log(res.plan_users);
                            $('#users').val(res.plan_users);
                            $('span#m_num_users').html(res.plan_users);
                            $('span#num_users').html(res.plan_users);
                            $('#users').prop("min",res.plan_users);
                            plan_users = res.plan_users;
                        }
                    })
                }else{
                    $('.pricing-rules').show();
                    $('#second_billing_type').hide();

                    $('#m_extra_users_row').hide();
                    $('#y_extra_users_row').hide();
                    $('span#m_num_users').html(1);
                    $('span#num_users').html(1);
                    $('#users').val(1);
                    $('#users').prop("min",1)
                }
            }

            if ($('input[type=radio]')) {
                $("#topup_instance").hide();
                $('#topup').off('click').on('click', function() {
                    console.log('inherited');
                    $("#topup_instance").show();
                    $("#new_instance").hide();
                    $('#top_up_instance_calculation').show();
                    $('#new_instance_calculation').hide();
                    $('#invoicing_policy').hide();
//                    $('#invoicing_policy1').val('normal');

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

                $('#new').off('click').on('click', function() {

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
                    $('#invoicing_policy').show();
                    type='new';
                })
            }

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

            $('#users').on('change',function(event) {
                var users = $(this).prop('min');
                var dy_users = document.getElementById('users').value;

//                if($('#invoicing_policy1').val() == 'user_plan_price'){
                if(invoicing_policy == 'user_plan_price'){
                    if(parseInt(dy_users) < parseInt(users)){
                        alert('No of users should be greater than plan users');
                        $(this).val(plan_users);
                        return false;
                    }
                }

                var m_extra_users = document.getElementById('m_extra_users');
                var m_extra_users_price = document.getElementById('m_extra_users_price')
                var m_num_users = document.getElementById('m_num_users');
                console.log($(this).prop('min')+',  '+m_num_users+'   '+ m_num_users.innerHTML);

                var num_users = document.getElementById('num_users');
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

                var extra_users = parseInt($(this).val())- parseInt(users)
                console.log(extra_users+'extra_users');

//                if($('#invoicing_policy1').val() == 'user_plan_price'){
                if(invoicing_policy == 'user_plan_price'){
                    m_extra_users_price.innerHTML = parseFloat(getUserProductPrice(extra_users)).toFixed(2);
                    m_extra_users.innerHTML = extra_users +  ' Users';

                    y_extra_users.innerHTML = extra_users +  ' Users';
                    y_extra_users_price.innerHTML = parseFloat(getUserProductPrice(extra_users) * 12).toFixed(2);
                    console.log(y_extra_users_price.innerHTML+", 0 "+m_extra_users_price.innerHTML+", "+extra_users)

                    if(extra_users > 0){
                        all_total.innerHTML = (parseFloat(a_p) + parseFloat(y_extra_users_price.innerHTML)).toFixed(2);
         				m_all_total.innerHTML = (parseFloat(m_a_p)+ parseFloat(m_extra_users_price.innerHTML)).toFixed(2);
                    }else{
                        all_total.innerHTML = (1 * parseFloat(a_p)).toFixed(2);
         				m_all_total.innerHTML = (1 * parseFloat(m_a_p)).toFixed(2);
                    }
                }else{
                    all_total.innerHTML = (n_u * parseFloat(a_p)).toFixed(2);
     				m_all_total.innerHTML = (m_n_u * parseFloat(m_a_p)).toFixed(2);
                }


            })

            function getUserProductPrice(qty){
                var ret = 0;
                $.ajax({
                    url : '/shop/get_user_product_price',
                    async : false,
                    data : { },
                    success : function(data) {
                        var res = JSON.parse(data);
                        console.log(res.price+'___________'+"price");
                        ret = res.price * parseInt(qty);
                    }
                })

                return parseFloat(ret)
            }

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



            $(document.getElementsByClassName('product_check'))
				.on('change',function() {

				   /////////////////////////////////////////////// Updated for is package product
					var pro_chk = document.getElementById(this.id);
					    var is_package = pro_chk.getAttribute('is_package')
                    if(is_package == "True"){
                        (pro_chk.checked == true)? is_package_count += 1 : is_package_count -= 1 ;
                        if((type == 'new')&&(is_package_count > 1)){
                            alert('Sorry ! You can not purchase two or more packages in one Order. You may select additional individual products instead.')
                            pro_chk.checked = false;
                            is_package_count -= 1;
                            return false;
                        }
                    }
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

					//extra users price
                     var m_extra_users_price = document.getElementById('m_extra_users_price')
                     var y_extra_users_price = document.getElementById('y_extra_users_price')


					var usersnum = document.getElementById('topup_users');
					var num_users = document.getElementById('num_users');
					var m_num_users = document.getElementById('m_num_users');

					var topup_apps = document.getElementById('topup_apps');
					var num_apps = document.getElementById('num_apps');
					var m_num_apps = document.getElementById('m_num_apps');

					var apps_price = document.getElementById('apps_price');
					var m_apps_price = document.getElementById('m_apps_price');
					var topup_apps_price = document.getElementById('topup_apps_price');

					var pro_chk = document.getElementById(this.id);

					var all_total = document.getElementById('all_total');
					var m_all_total = document.getElementById('m_all_total');
					var topup_all_total = document.getElementById('topup_all_total');

					var pro_price = pro_chk.getAttribute('pro_price');
					pro_price = (!pro_price)?0.00:pro_price;

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

                    var m_extra_users = $('#users').val()-$('#users').prop('min')


					if (pro_chk.checked == true) {
						apps_price.innerHTML = (parseFloat(a_p) + parseFloat(pro_price * 12)).toFixed(2);
						console.log(m_a_p,'----------', pro_price)

						m_apps_price.innerHTML = (parseFloat(m_a_p) + parseFloat(pro_price)).toFixed(2);
						num_apps.innerHTML = (apps + 1) + ' Apps';
						m_num_apps.innerHTML = (apps + 1) + ' Apps';
						topup_apps.innerHTML = (apps + 1) + ' Apps';

//						if($('#invoicing_policy1').val() == 'user_plan_price'){
                        if(invoicing_policy == 'user_plan_price'){
						    if(m_extra_users > 0){
    						    m_extra_users_price.innerHTML = parseFloat(getUserProductPrice(m_extra_users)).toFixed(2);
    						    y_extra_users_price.innerHTML = parseFloat(getUserProductPrice(m_extra_users) * 12).toFixed(2);
    						    console.log(y_extra_users_price.innerHTML+", 1 "+m_extra_users_price.innerHTML+", "+m_extra_users)
                                all_total.innerHTML = (parseFloat(total) + parseFloat(pro_price * 12)).toFixed(2); // +  parseFloat(y_extra_users_price.innerHTML)
						     	m_all_total.innerHTML = (parseFloat(m_total) + parseFloat(pro_price) ).toFixed(2); // + parseFloat(m_extra_users_price.innerHTML)
                            }else{
//                                m_extra_users_price.innerHTML = parseFloat(getUserProductPrice(0)).toFixed(2);
//    						    y_extra_users_price.innerHTML = parseFloat(getUserProductPrice(0)).toFixed(2);
                                all_total.innerHTML = (total + parseFloat(pro_price * 12 * 1)).toFixed(2);
                                m_all_total.innerHTML = (m_total + parseFloat(pro_price * 1)).toFixed(2);
                            }

                        }else{
                            all_total.innerHTML = (total + parseFloat(pro_price * 12 * n_u)).toFixed(2);
                         	m_all_total.innerHTML = (m_total + parseFloat(pro_price * m_n_u)).toFixed(2);
                        }

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

//                        if($('#invoicing_policy1').val() == 'user_plan_price'){
                          if(invoicing_policy == 'user_plan_price'){
                             if(m_extra_users > 0){
                                m_extra_users_price.innerHTML = parseFloat(getUserProductPrice(m_extra_users)).toFixed(2);
    						    y_extra_users_price.innerHTML = parseFloat(getUserProductPrice(m_extra_users) * 12).toFixed(2);
    						    console.log(y_extra_users_price.innerHTML+", 2 "+m_extra_users_price.innerHTML+", "+m_extra_users)
                                m_all_total.innerHTML = (parseFloat(m_total) - parseFloat(pro_price ) ).toFixed(2); //- m_extra_users_price.innerHTML
                                all_total.innerHTML = (parseFloat(total) - parseFloat(pro_price * 12 ) ).toFixed(2); //- y_extra_users_price.innerHTML
                             }else{
//                                m_extra_users_price.innerHTML = parseFloat(getUserProductPrice(0)).toFixed(2);
//    						    y_extra_users_price.innerHTML = parseFloat(getUserProductPrice(0)).toFixed(2);
                                m_all_total.innerHTML = (m_total - parseFloat(pro_price * 1)).toFixed(2);
                                all_total.innerHTML = (total - parseFloat(pro_price * 12 * 1)).toFixed(2);
                             }
                        }else{
                            all_total.innerHTML = (total - parseFloat(pro_price * 12 * n_u)).toFixed(2);
                            m_all_total.innerHTML = (m_total - parseFloat(pro_price * m_n_u)).toFixed(2);
                        }

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

//            $('#invoicing_policy1').on('change',function(){
//                var val = $(this).val();
//                if(val == 'user_plan_price'){
//                $('#m_extra_users_row').show();
//                $('#y_extra_users_row').show();
//
//                    $.ajax({
//                        url : '/shop/get_default_plan_users',
//                        async : false,
//                        data : {
//                            val : val,
//                        },
//                        success : function(data) {
//                            var res = JSON.parse(data);
//                            console.log(res.plan_users);
//                            $('#users').val(res.plan_users);
//                            $('span#m_num_users').html(res.plan_users);
//                            $('#users').prop("min",res.plan_users)
//                        }
//                    })
//                }else{
//                    $('#m_extra_users_row').hide();
//                    $('#y_extra_users_row').hide();
//                    $('span#m_num_users').html(1);
//                    $('#users').val(1);
//                    $('#users').prop("min",1)
//                }
//            })


			$('#pay').off('click').on('click',function() {
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

                        var language = document.getElementById('language').value;
                        if(!language){
                            alert('Please Select Language');
                            return false
                        }

//                        if(parseInt($('#all_total').text()) < 1){
//                            alert("please select atleast one product!")
//                            return false
//                        }

                        for (var i = 0; i < checkboxes.length; i++) {
                            if (checkboxes[i].checked) {
                                if (ids.length < 1) {
                                    ids = checkboxes[i].getAttribute('pro_id');
                                } else {
                                    ids = ids + "," + checkboxes[i].getAttribute('pro_id');
                                }
                            }
                        }
//                        var billing_type = $('#invoicing_policy1').val()
                          var billing_type = invoicing_policy
                        $.ajax({
                                url : '/shop/checkout2buy',
                                async : false,
                                data : {
                                    term : selected_term,
                                    ids : ids,
                                    dbname : dbname,
                                    num : dy_users,
                                    new_instance: true,
                                    billing_type : billing_type,
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


        })

	})