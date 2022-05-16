$(document).ready(function() {
    $('#domain_chain_crt_alert').hide();
    $('#domain_crt_alert').hide();
    $('#domain_key_alert').hide();
    $('#domain_key_val_alert').hide();
    $('#domain_crt_val_alert').hide();
    $('#domain_chain_crt_val_alert').hide();
    $('#web_conf_val').hide();
    var web_conf_val = $('#web_conf_val').text();
    var type ='http'
    var db_name


    $('#cancel_btn').on('click',function(){
        document.getElementById("domain_form").reset();
        $('#myModal').hide();
        window.location.reload();
    });

    $('.domain_btn').on('click',function(){
        document.getElementById("domain_form").reset();
        db_name = $(this).parent().attr('id')
        $('#myModal').show();
        $('#db_name').val(db_name)
        $('#domain').val(type)
    });
    $('#domain_type ').change(function(){
        type = this.value
        $('#domain').val(type)
        if (type == 'https'){
            $('.https_tr').removeAttr('style')
            $('#domain_key').attr('required','True')
            $('#domain_crt').attr('required','True')
            if (web_conf_val == 'nginx'){
            $('#domain_chain_crt').attr('required','True')
            };
            if (web_conf_val == 'apache'){
            $('#domain_chain_crt').removeAttr('required')
            };
        };
        if (type == 'http'){
            $('.https_tr').hide();
            $('#domain_key').removeAttr('required')
            $('#domain_crt').removeAttr('required')
            $('#domain_chain_crt').removeAttr('required')
        };
    });
    $('#domain_form').submit(function(e){
        $('#myModal').hide();
        window.location.reload();
    });
    $('#submit_btn').on('click',function(){
            var domainKeyFileSelector = document.getElementById('domain_key');
            domainKeyFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                console.log(fileList);
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_key_text', text);
                };
                reader.readAsText(fileList[0]);
            });
            var domainCrtFileSelector = document.getElementById('domain_crt');
            domainCrtFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                console.log(fileList);
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_crt_text', text);
                };
                reader.readAsText(fileList[0]);
            });
            var domainChainCrtFileSelector = document.getElementById('domain_chain_crt');
            domainChainCrtFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                console.log(fileList);
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_chain_crt_text', text);
                };
                reader.readAsText(fileList[0]);
            });
          var domain_key_text = sessionStorage.getItem('domain_key_text');
          var domain_crt_text = sessionStorage.getItem('domain_crt_text');
          var domain_chain_crt_text = sessionStorage.getItem('domain_chain_crt_text');
          var string1 = '-----BEGIN CERTIFICATE-----'
          var string2 = '-----END CERTIFICATE-----'
          if (domain_key_text){
            var domain_key_first_text = domain_key_text.split('\n')[0];
            var key_result = domain_key_first_text.localeCompare(string1)
          };
          if (domain_crt_text){
            var domain_crt_first_text = domain_crt_text.split('\n')[0];
            var crt_result = domain_crt_first_text.localeCompare(string1)
          };
          if(domain_chain_crt_text){
            var domain_chain_first_text = domain_chain_crt_text.split('\n')[0];
            var chain_result = domain_chain_first_text.localeCompare(string1)
          };

          var client_domain = $('#client_domain').val()
          var domain_key = $('#domain_key').val()
          var domain_crt = $('#domain_crt').val()
          var domain_chain_crt = $('#domain_chain_crt').val()
          var domain_chain_crt_ext = domain_chain_crt.split('.').pop()
            if (type == 'https'){
            console.log(" type http")
                if(domain_crt && domain_key)
                {
                    var domain_key_ext = domain_key.split('.').pop()
                    var domain_crt_ext = domain_crt.split('.').pop()
                    if (domain_crt_ext == 'crt' && domain_key_ext == 'txt')
                    {
                        $('#domain_key_alert').hide();
                        $('#domain_crt_alert').hide();
                        if (key_result == 0  && (domain_key_text.includes(string2)) && crt_result == 0  && (domain_crt_text.includes(string2)))
                        {
                            $('#domain_key_val_alert').hide();
                            $('#domain_crt_val_alert').hide();
                            if (domain_chain_crt)
                            {
                                    if (domain_chain_crt)
                                    {

                                        if(domain_chain_crt_ext == 'crt'){

                                            $('#domain_chain_crt_alert').hide();
                                             if (domain_chain_crt_text.includes(string2)  && chain_result == 0)
                                             {
                                                   $('#domain_chain_crt_val_alert').hide();
                                                   $('#submit_btn').attr("type", "submit");
                                             }
                                             else{
                                                $('#domain_chain_crt_val_alert').show();
                                             };
                                        }
                                        else
                                        {
                                            $('#domain_chain_crt_alert').show();
                                        };
                                    };

                            }
                            else{
                                $('#submit_btn').attr("type", "submit");
                            };

                        }
                        else
                        {
                            if(key_result !== 0  || (!(domain_key_text.includes(string2))))
                            {

                                $('#domain_key_val_alert').show();
                            }
                            else{
                                $('#domain_key_val_alert').hide();
                            };
                            if(crt_result !== 0  || (!(domain_crt_text.includes(string2))))
                            {

                                $('#domain_crt_val_alert').show();
                            }
                            else{
                                $('#domain_crt_val_alert').hide();
                            };
                        };

                    }
                    else{
                        if(domain_crt_ext !== 'crt')
                        {
                            $('#domain_crt_alert').show();
                        }
                        else
                        {
                            $('#domain_crt_alert').hide();
                        };
                        if (domain_key_ext !== 'txt')
                        {
                            $('#domain_key_alert').show();
                        }
                        else
                        {
                             $('#domain_key_alert').hide();
                        };
                        if (domain_chain_crt && domain_chain_crt_ext !== 'crt')
                        {
                            $('#domain_chain_crt_alert').show();
                        }
                        else
                        {
                            if (web_conf_val == 'nginx')
                            {
                                 $('#domain_chain_crt_alert').hide();
                            };
                        };
                    };
                }

                else{

                    $('#submit_btn').attr("type", "submit");
                };
            };

            if (type == 'http'){
            $('#submit_btn').attr("type", "submit");
            };
    });
});