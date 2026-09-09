$(document).ready(function() {
    // ============================================
    // 1. TAGS - GESTIÓN DE TEMAS DE BÚSQUEDA
    // ============================================
    var topics = [];

    function updateTags() {
        var $list = $('#tagsList');
        $list.empty();
        
        topics.forEach(function(topic, index) {
            var $tag = $('<span class="tag-item">')
                .text(topic)
                .append($('<button class="remove-tag">')
                    .html('×')
                    .attr('type', 'button')
                    .click(function() {
                        topics.splice(index, 1);
                        updateTags();
                        updateHiddenTopics();
                    })
                );
            $list.append($tag);
        });
        
        updateHiddenTopics();
    }

    function updateHiddenTopics() {
        $('#topicsHidden').val(topics.join(', '));
    }

    $('#searchTopics').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            var value = $(this).val().trim();
            if (value && topics.length < 20) {
                topics.push(value);
                $(this).val('');
                updateTags();
            } else if (topics.length >= 20) {
                alert('⚠️ Has alcanzado el límite máximo de 20 temas.');
            }
        }
    });

    // ============================================
    // 2. PRECIO AUTOMÁTICO (Cantidad × 100 CUP)
    // ============================================
    function updatePrice() {
        var count = parseInt($('#referenceCount').val()) || 0;
        
        if (count < 1) {
            $('#priceDisplay').text('0.00');
            $('#price').val(0);
            return;
        }
        
        if (count > 300) {
            alert('⚠️ La cantidad máxima de referencias es 300.');
            $('#referenceCount').val(300);
            count = 300;
        }
        
        var price = count * 100;
        $('#priceDisplay').text(price.toFixed(2));
        $('#price').val(price);
    }

    $('#referenceCount').on('input', updatePrice);
    updatePrice();

    // ============================================
    // 3. SIGNATURE PAD
    // ============================================
    $('#signaturePad').jSignature({
        'width': '100%',
        'height': 200,
        'color': '#1a3a5c',
        'background': '#ffffff',
        'lineWidth': 2,
        'decorColor': '#ddd'
    });

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
    // 4. LIMPIAR FIRMA
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
    // 5. DETECTAR FIRMA
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
        var topicsValue = $('#topicsHidden').val().trim();
        var count = parseInt($('#referenceCount').val()) || 0;
        var date = $('#deliveryDate').val();

        if (!name || !id || !address || !institution || !topicsValue) {
            alert('⚠️ Por favor, completa todos los campos obligatorios e incluye al menos un tema de búsqueda.');
            return false;
        }

        if (!/^\d{11}$/.test(id)) {
            alert('⚠️ El Carnet de Identidad debe tener 11 dígitos numéricos.');
            return false;
        }

        if (count < 1 || count > 300) {
            alert('⚠️ La cantidad de referencias debe ser entre 1 y 300.');
            return false;
        }

        if (!date) {
            alert('⚠️ Por favor, selecciona una fecha de entrega.');
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
            url: '/generar-pdf/busqueda',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhrFields: {
                responseType: 'blob'
            },
            success: function(data, status, xhr) {
                $('#loadingMessage').hide();
                $('#generateBtn').prop('disabled', false);

                var contentType = xhr.getResponseHeader('Content-Type');
                
                if (contentType && contentType.includes('application/pdf')) {
                    var blob = new Blob([data], { type: 'application/pdf' });
                    var link = document.createElement('a');
                    link.href = window.URL.createObjectURL(blob);
                    link.download = 'carta_compromiso_busqueda.pdf';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(link.href);

                    mostrarExitoYRedirigir();
                } else {
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
                if (xhr.responseText && xhr.responseText.length < 200) {
                    errorMsg = xhr.responseText;
                }
                alert(errorMsg);
            }
        });
    });

    // ============================================
    // 7. FUNCIÓN: MOSTRAR ÉXITO Y REDIRIGIR
    // ============================================
    function mostrarExitoYRedirigir() {
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

    // Estado inicial de la firma
    setTimeout(checkSignature, 500);

    // Inicializar precio
    updatePrice();
});