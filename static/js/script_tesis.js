$(document).ready(function() {
    // ============================================
    // 1. PRICE CONFIGURATION
    // ============================================
    const prices = {
        'Pregrado': 80,
        'Diplomado': 80,
        'Especializacion': 80,
        'Maestria': 100,
        'Doctorado': 100
    };

    const currencySymbols = {
        'USD': '$',
        'EUR': '€',
        'MLC': 'MLC ',
        'CUP': 'CUP '
    };

    function updatePrice() {
        const level = $('#academicLevel').val();
        const currency = $('#currency').val();
        const symbol = currencySymbols[currency] || '$';
        const price = prices[level] || 0;

        $('#currencySymbol').text(symbol);
        $('#priceDisplay').text(price.toFixed(2));
        $('#price').val(price);
    }

    $('#academicLevel').on('change', updatePrice);
    $('#currency').on('change', updatePrice);
    updatePrice();

    // ============================================
    // 2. SIGNATURE PAD - CONFIGURACIÓN
    // ============================================
    $('#signaturePad').jSignature({
        'width': '100%',
        'height': 200,
        'color': '#1a3a5c',
        'background': '#ffffff',
        'lineWidth': 2,
        'decorColor': '#ddd'
    });

    // ============================================
    // 3. FUNCIÓN PARA OBTENER FIRMA
    // ============================================
    function getSignatureData() {
        try {
            var data = $('#signaturePad').jSignature('getData', 'image');
            if (Array.isArray(data) && data.length > 1) {
                return data[1];
            }
            return data;
        } catch(e) {
            return null;
        }
    }

    // ============================================
    // 4. BOTÓN "LIMPIAR FIRMA"
    // ============================================
    $('#clearSignature').click(function() {
        $('#signaturePad').jSignature('reset');
        $('#signatureData').val('');
        $('#signaturePad').css({
            'border-color': '#ccc',
            'border-style': 'dashed',
            'border-width': '2px'
        });
        $('#signaturePad').removeClass('has-signature');
    });

    // ============================================
    // 5. DETECTAR CUANDO EL USUARIO FIRMA
    // ============================================
    function checkSignature() {
        var data = getSignatureData();
        var hasData = data && data.length > 100;
        
        if (hasData) {
            $('#signaturePad').css({
                'border-color': '#2d7d46',
                'border-style': 'solid',
                'border-width': '2px'
            });
            $('#signaturePad').addClass('has-signature');
        } else {
            $('#signaturePad').css({
                'border-color': '#ccc',
                'border-style': 'dashed',
                'border-width': '2px'
            });
            $('#signaturePad').removeClass('has-signature');
        }
        return hasData;
    }

    $('#signaturePad').on('change', function() {
        checkSignature();
    });

    $(document).on('mouseup touchend', function() {
        setTimeout(checkSignature, 100);
    });

    // ============================================
    // 6. ENVÍO DEL FORMULARIO CON AJAX
    // ============================================
    $('#commitmentForm').on('submit', function(e) {
        e.preventDefault();

        // Validar campos obligatorios
        var name = $('#clientName').val().trim();
        var id = $('#clientId').val().trim();
        var address = $('#clientAddress').val().trim();
        var institution = $('#institution').val().trim();
        var topic = $('#thesisTopic').val().trim();
        var date = $('#deliveryDate').val();

        if (!name || !id || !address || !institution || !topic || !date) {
            alert('⚠️ Por favor, completa todos los campos obligatorios.');
            return false;
        }

        if (!/^\d{11}$/.test(id)) {
            alert('⚠️ El Carnet de Identidad debe tener 11 dígitos numéricos.');
            return false;
        }

        // Obtener firma
        var signatureData = getSignatureData();
        if (signatureData) {
            $('#signatureData').val(signatureData);
        }

        // Mostrar mensaje de carga
        $('#loadingMessage').show();
        $('#generateBtn').prop('disabled', true);

        // Preparar datos para AJAX
        var formData = new FormData(this);

        // Enviar con AJAX
        $.ajax({
            url: '/generar-pdf/tesis',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhrFields: {
                responseType: 'blob' // Para manejar el PDF como blob
            },
            success: function(data, status, xhr) {
                // Ocultar mensaje de carga
                $('#loadingMessage').hide();
                $('#generateBtn').prop('disabled', false);

                // Verificar si es un error (HTML) o un PDF
                var contentType = xhr.getResponseHeader('Content-Type');
                
                if (contentType && contentType.includes('application/pdf')) {
                    // Crear un enlace para descargar el PDF
                    var blob = new Blob([data], { type: 'application/pdf' });
                    var link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.download = 'carta_compromiso.pdf';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(link.href);

                    // Mostrar mensaje de éxito y redirigir
                    mostrarExitoYRedirigir();
                } else {
                    // Si llegó HTML, es un error
                    var reader = new FileReader();
                    reader.onload = function() {
                        alert('❌ Error: ' + reader.result);
                    };
                    reader.readAsText(data);
                }
            },
            error: function(xhr, status, error) {
                $('#loadingMessage').hide();
                $('#generateBtn').prop('disabled', false);
                
                var errorMsg = '❌ Error al generar el documento. Intenta nuevamente.';
                if (xhr.responseText) {
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response.error) errorMsg = response.error;
                    } catch(e) {
                        // Si no es JSON, mostrar el texto
                        if (xhr.responseText.length < 200) {
                            errorMsg = xhr.responseText;
                        }
                    }
                }
                alert(errorMsg);
            }
        });
    });

    // ============================================
    // 7. FUNCIÓN: MOSTRAR ÉXITO Y REDIRIGIR
    // ============================================
    function mostrarExitoYRedirigir() {
        // Crear overlay personalizado
        var overlay = $('<div id="successOverlay" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;">');
        
        var modal = $('<div style="background:white;border-radius:16px;padding:40px;max-width:450px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.3);">');
        
        modal.append('<div style="font-size:60px;margin-bottom:15px;">✅</div>');
        modal.append('<h2 style="color:#1a3a5c;margin-bottom:10px;">¡Documento Generado!</h2>');
        modal.append('<p style="color:#666;font-size:16px;line-height:1.5;margin-bottom:20px;">La carta de compromiso se ha generado correctamente.<br>El PDF se ha descargado automáticamente.</p>');
        
        var btnAceptar = $('<button id="successBtn" style="background:linear-gradient(135deg,#1a3a5c,#2d7d46);color:white;border:none;padding:12px 40px;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:all 0.3s;">Aceptar</button>');
        btnAceptar.hover(
            function() { $(this).css('transform', 'scale(1.05)'); },
            function() { $(this).css('transform', 'scale(1)'); }
        );
        
        btnAceptar.click(function() {
            window.location.href = '/';
        });
        
        modal.append(btnAceptar);
        overlay.append(modal);
        $('body').append(overlay);
    }

    // ============================================
    // 8. VALIDACIONES ADICIONALES
    // ============================================
    $('#deliveryDate').on('change', function() {
        if ($(this).val()) {
            const selectedDate = new Date($(this).val());
            const currentDate = new Date();
            currentDate.setHours(0, 0, 0, 0);
            if (selectedDate < currentDate) {
                alert('⚠️ La fecha de entrega debe ser posterior a la fecha actual.');
                $(this).val('');
            }
        }
    });

    $('#clientId').on('input', function() {
        this.value = this.value.replace(/\D/g, '').slice(0, 11);
    });

    // Estado inicial
    setTimeout(checkSignature, 500);
});