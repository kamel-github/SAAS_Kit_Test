odoo.define('saas_product.manage_database', function(require) {
	"use strict";
	var ajax = require('web.ajax');
	$(document).ready(function() {
		$("#save_users").hide();
		$("#decrease_user_span").hide();
		$("#user_alert").hide();
		$("#db_alert").hide();
		$("#db_size_note").hide();
		$("#filestore_size_note").hide();
		$("#filestore_alert").hide();
		$("#user_count_alert").hide();
		$("#decrease_user_note").hide();
		$("#save_db_size").hide();
		$("#save_filestore_size").hide();
	})
	
	
	//Start
	$(function() {
//	user decrease
	$('#save_user_decrease').on('click', function() {
	        $("#decrease_user_note").hide();
			console.log("yes!!!")
			var db_name = $('#db_name_xml').text()
			var user_count_decrease = $('#user_count_decrease').val()
			console.log(user_count_decrease)
			if (parseInt(user_count_decrease) == 0){
				alert("Value should be more than zero")
				return false
			}
			$.ajax({
				url : '/apps/decrease_users',
				type : 'POST',
				async : false,
				data : {
					db : db_name,
					users : user_count_decrease
				},
				success : function(data) {
                    data = parseInt(data)
                    if (data>0){
                        $("#user_alert").hide();
                        $("#user_count_alert").hide();
                        $("#decrease_user_span").hide();
                        $("#update_user").show();
                        $("#decrease_user").show();
                        $("#update_user").text(data);
                        $("#update_user2").text(data);
                        location.reload();
                    }
					else if(data == 0){
					    $("#user_alert").show();
					    $("#user_count_alert").hide();

					}
					else if(data == -1){
					    $("#user_count_alert").show();
					    $("#user_alert").hide();
					}

					else{
					    alert("Something wrong please try again")
					    $("#user_alert").hide();
					    $("#user_count_alert").hide();
					    location.reload();
					}

				},
				failure : function(data) {
					alert("Some Error!!")
				}

            })
        })

		$('#save_user').on('click', function() {
			console.log("yes!!!")
			var db_name = $('#db_name_xml').text()
			var user_count = $('#num_user').val()
			
			if (parseInt(user_count) == 0){
				alert("Value should be more than zero")
				return false
			}

			$.ajax({
				url : '/apps/add_more_users',
				type : 'POST',
				async : false,
				data : {
					db : db_name,
					users : user_count
				},
				success : function(data) {
                    data = parseInt(data)
                    if (data>0){
                        $("#save_users").hide();
                        $("#update_user").show();
                        $("#show_user").show();
                        $("#update_user").text(data);
                        $("#update_user2").text(data);
                        window.location.href = "/shop/cart";
                    }
					else {
					    location.reload();
					}

				},
				failure : function(data) {
					alert("Some Error!!")
				}
			})

		})

	})//End
	$(function() {
        $('#show_db_size').on('click', function() {
                $("#db_size_note").show();
                $('#show_db_size').hide()
                $('#db_size').hide()
                $("#save_db_size").show();
        })
    })
    $(function() {
        $('.db_cancel').on('click', function() {
                $("#db_size_note").hide();
                $("#db_alert").hide()
                $('#show_db_size').show()
                $('#db_size').show()
                $("#save_db_size").hide();
        })
    })

    $(function() {
        $('#show_filestore_size').on('click', function() {
                $('#filestore_size_note').show()
                $('#show_filestore_size').hide()
                $('#filestore_size').hide()
                $("#save_filestore_size").show();
        })
    })
    $(function() {
        $('.filestore_cancel').on('click', function() {
                $('#filestore_size_note').hide()
                $("#filestore_alert").hide()
                $('#show_filestore_size').show()
                $('#filestore_size').show()
                $("#save_filestore_size").hide();
        })
    })
    $(function() {
        $('#confirm_db_size').on('click', function() {
            var db_name = $('#db_name_xml').text()
            var size = $("#num_db_size").val()
            if(size>0){
                $("#db_alert").hide()
                $.ajax({
				url : '/add_db_size',
				type : 'POST',
				async : false,
				data : {
					db : db_name,
					size : size
				},
				success : function(data) {
                    data = parseInt(data)
                    if (data>0){
                        window.location.href = "/shop/cart";
                        sessionStorage.setItem('space_product', "db");
                    }
					else {
					    location.reload();
					}

				},
				failure : function(data) {
					alert("Some Error!!")
				}
			})

            }
            else{
                $("#db_alert").show()
            }
        })
        $('#confirm_filestore_size').on('click', function() {
            var db_name = $('#db_name_xml').text()
            var size = $("#num_filestore_size").val()
            if(size>0){
                $("#filestore_alert").hide()
                $.ajax({
				url : '/add_filestore_size',
				type : 'POST',
				async : false,
				data : {
					db : db_name,
					size : size
				},
				success : function(data) {
                    data = parseInt(data)
                    if (data>0){
                        window.location.href = "/shop/cart";
                        sessionStorage.setItem('space_product', "filestore");
                    }
					else {
					    location.reload();
					}

				},
                error: function (data) {
                        console.error("ERROR ", data);
                    },
				failure : function(data) {
					alert("Some Error!!")
				}
			})

            }
            else{
                $("#filestore_alert").show()
            }
        })
    })


	
	//Start
	$(function() {
		$('.deact').on('click', function() {
			var login = $(this).attr('login');
			var db = $(this).attr('db');
			$.ajax({
				url : '/apps/remove_users',
				type : 'POST',
				async : false,
				data : {
					user : login,
					db : db
				},
				success : function(data) {
					location.reload();

				},
				failure : function(data) {
				}
			})

		})
	})
	//End
	
	//Start
	$(function() {
		$('.react').on('click', function() {
			var self = this
			var login = $(this).attr('login');
			var db = $(this).attr('db');
			$.ajax({
				url : '/apps/activate_user_again',
				type : 'POST',
				async : false,
				data : {
					user : login,
					db : db
				},
				success : function(data) {
					var res = JSON.parse(data)
					console.log('=========================================')
					console.log(res)
					console.log(res.allow)
					console.log(res['allow'])
					console.log('++++++++++++++++++++++++++++')
					if (res.allow == true){
						location.reload();
					}
					else{
						$(self).parent().append("<p><font color='red' >Can't activate more than Purchased Users</font></p>")
					}

				},
				failure : function(data) {
				}
			})
		})
	})//End
	
	
	
	//Start
	$(function() {
		$('#show_user').on('click', function() {
		    $("#decrease_user_note").hide();
			$("#save_users").show();
			$("#add_text_id").show();
            $('#decrease_user').hide();
			$("#update_user").hide();
			$("#show_user").hide();

		})
	})//End
	$(function() {
		$('#decrease_user').on('click', function() {
		    $("#decrease_user_note").show();
			$("#decrease_user_span").show();
			$("#decrease_text_id").show();
            $('#show_user').hide();
			$("#update_user").hide();
			$("#decrease_user").hide();

		})
	})

	
	//Start
	$(function() {
		$('.id_cancel').on('click', function() {
		    $("#decrease_user_note").hide();
		    $("#user_alert").hide();
			$("#save_users").hide();
			$("#update_user").show();
			$("#add_text_id").hide();
			$("#show_user").show();
			$("#decrease_user_span").hide();
			$("#decrease_text_id").hide();
			$("#decrease_user").show();
			$("#user_count_alert").hide();

		})
	})

})