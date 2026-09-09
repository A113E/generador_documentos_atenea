$(document).ready(function() {
    // ============================================
    // 1. CONFIGURACIÓN DE SERVICIOS
    // ============================================
    const serviceConfig = {
        'confeccion_articulo': {
            label: 'Confección de artículo completo + envío a revista',
            descripcion: 'Elaboración completa del artículo científico con todas las secciones (IMRYD), análisis estadístico, tablas y gráficos. Incluye selección de revista, adaptación a normas, envío y seguimiento de revisiones. Cubre una revista. Reenvío a otra revista: +$25 USD.',
            precio_base: 50,
            precio_extra: { 'original': 0, 'revision': 10, 'ensayo': 20, 'otros': 0 }
        },
        'revision_articulo': {
            label: 'Revisión de artículo (sugerencias o adaptación a formato)',
            descripcion: 'Revisión exhaustiva del artículo con sugerencias de mejora en estructura, contenido, redacción y formato, o adaptación al formato específico de la revista seleccionada. No incluye corrección directa del texto.',
            precio_fijo: 40
        },
        'revision_bibliografica': {
            label: 'Revisión bibliográfica',
            descripcion: 'Búsqueda y/o revisión de referencias bibliográficas según la norma seleccionada. El precio se calcula multiplicando la cantidad de referencias por 100 CUP.',
            precio_fijo: 0,
            isVariable: true
        }
    };

    var selectedServices = [];

    // ============================================
    // 2. PRICE CONFIGURATION
    // ============================================
    const currencySymbols = {
        'USD': '$',
        'EUR': '€',
        'MLC': 'MLC ',
        'CUP': 'CUP '
    };

    // Precios por tipo de artículo
    const articlePrices = {
        'original': 50,
        'revision': 60,
        'ensayo': 70,
        'otros': 50
    };

    function updatePrice() {
        var totalPrice = 0;
        var currency = $('#currency').val();
        var symbol = currencySymbols[currency] || '$';
        var articleType = $('#articleType').val();
        var hasBibliografia = false;
        var refCount = parseInt($('#referenceCount').val()) || 0;

        selectedServices.forEach(function(serviceKey) {
            var config = serviceConfig[serviceKey];
            if (config) {
                if (config.isVariable) {
                    hasBibliografia = true;
                } else if (config.precio_fijo !== undefined) {
                    totalPrice += config.precio_fijo;
                } else {
                    // Confección de artículo: precio base + extra por tipo
                    var basePrice = config.precio_base || 50;
                    var extra = config.precio_extra[articleType] || 0;
                    totalPrice += basePrice + extra;
                }
            }
        });

        // Si hay revisión bibliográfica, sumar el precio variable
        if (hasBibliografia && refCount > 0) {
            totalPrice += refCount * 100;
        }

        // Mostrar precio en la moneda seleccionada
        var displayPrice = totalPrice;
        if (currency !== 'CUP' && hasBibliografia) {
            var exchangeRate = 265;
            if (currency === 'USD') {
                displayPrice = (totalPrice / exchangeRate).toFixed(2);
            } else if (currency === 'EUR') {
                displayPrice = (totalPrice / (exchangeRate * 1.05)).toFixed(2);
            } else {
                displayPrice = totalPrice.toFixed(2);
            }
        } else if (currency === 'CUP') {
            displayPrice = totalPrice.toFixed(2);
        } else {
            displayPrice = totalPrice.toFixed(2);
        }

        $('#currencySymbol').text(symbol);
        $('#priceDisplay').text(displayPrice);
        $('#price').val(totalPrice);
    }

    // ============================================
    // 3. SERVICIOS TAGS - SELECCIÓN
    // ============================================
    function toggleService(serviceKey) {
        var index = selectedServices.indexOf(serviceKey);
        if (index === -1) {
            selectedServices.push(serviceKey);
        } else {
            selectedServices.splice(index, 1);
        }
        updateUI();
    }

    function updateUI() {
        // Actualizar botones
        $('.service-tag').each(function() {
            var service = $(this).data('service');
            if (selectedServices.indexOf(service) !== -1) {
                $(this).addClass('active');
            } else {
                $(this).removeClass('active');
            }
        });

        // Actualizar lista de seleccionados
        var $list = $('#selectedServicesList');
        $list.empty();
        selectedServices.forEach(function(serviceKey) {
            var config = serviceConfig[serviceKey];
            if (config) {
                var $tag = $('<span class="tag-item">')
                    .text(config.label)
                    .append($('<button class="remove-tag">')
                        .html('×')
                        .attr('type', 'button')
                        .click(function() {
                            toggleService(serviceKey);
                        })
                    );
                $list.append($tag);
            }
        });

        // Actualizar descripciones
        var $descContainer = $('#serviceDescriptions');
        $descContainer.empty();
        selectedServices.forEach(function(serviceKey) {
            var config = serviceConfig[serviceKey];
            if (config) {
                var priceInfo = '';
                var articleType = $('#articleType').val();
                if (config.isVariable) {
                    priceInfo = 'Precio: Cantidad × 100 CUP';
                } else if (config.precio_fijo !== undefined) {
                    priceInfo = 'Precio: $' + config.precio_fijo + ' USD';
                } else {
                    var base = config.precio_base || 50;
                    var extra = config.precio_extra[articleType] || 0;
                    var total = base + extra;
                    priceInfo = 'Precio: $' + total + ' USD';
                }
                var $desc = $('<div class="service-description">')
                    .html('<strong>' + config.label + ':</strong> ' + config.descripcion + ' <span class="price-detail">(' + priceInfo + ')</span>');
                $descContainer.append($desc);
            }
        });

        // Mostrar/ocultar campo de cantidad de referencias
        var hasBibliografia = selectedServices.indexOf('revision_bibliografica') !== -1;
        if (hasBibliografia) {
            $('#referenceCountField').show();
        } else {
            $('#referenceCountField').hide();
            $('#referenceCount').val('');
        }

        // Actualizar precio
        updatePrice();
        updateHiddenFields();
    }

    function updateHiddenFields() {
        $('#selectedServicesHidden').val(selectedServices.join(','));
    }

    // Eventos de selección de servicios
    $('.service-tag').click(function() {
        var service = $(this).data('service');
        toggleService(service);
    });

    // ============================================
    // 4. EVENTOS DE ACTUALIZACIÓN DE PRECIO
    // ============================================
    $('#articleType').on('change', function() {
        updateUI();
        updatePrice();
    });

    $('#currency').on('change', function() {
        updatePrice();
    });

    $('#referenceCount').on('input', function() {
        var val = parseInt($(this).val()) || 0;
        if (val > 300) {
            alert('⚠️ La cantidad máxima de referencias es 300.');
            $(this).val(300);
        }
        updatePrice();
    });

    // ============================================
    // 5. SELECCIÓN DE REVISTA - Mostrar/Ocultar campo
    // ============================================
    $('#journalOption').on('change', function() {
        if ($(this).val() === 'cliente') {
            $('#journalNameField').show();
        } else {
            $('#journalNameField').hide();
            $('#journalName').val('');
        }
    });
    // Estado inicial
    if ($('#journalOption').val() === 'cliente') {
        $('#journalNameField').show();
    } else {
        $('#journalNameField').hide();
    }

    // ============================================
    // 6. SIGNATURE PAD
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
    // 7. LIMPIAR FIRMA
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
    // 8. DETECTAR FIRMA
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
    // 9. ENVÍO DEL FORMULARIO CON AJAX
    // ============================================
    $('#commitmentForm').on('submit', function(e) {
        e.preventDefault();

        // Validar campos obligatorios
        var name = $('#clientName').val().trim();
        var id = $('#clientId').val().trim();
        var address = $('#clientAddress').val().trim();
        var institution = $('#institution').val().trim();
        var title = $('#articleTitle').val().trim();
        var type = $('#articleType').val();
        var topic = $('#articleTopic').val().trim();
        var date = $('#deliveryDate').val();

        if (!name || !id || !address || !institution || !title || !type || !topic || !date) {
            alert('⚠️ Por favor, completa todos los campos obligatorios.');
            return false;
        }

        if (!/^\d{11}$/.test(id)) {
            alert('⚠️ El Carnet de Identidad debe tener 11 dígitos numéricos.');
            return false;
        }

        if (selectedServices.length === 0) {
            alert('⚠️ Por favor, selecciona al menos un servicio.');
            return false;
        }

        // Si hay revisión bibliográfica, validar cantidad
        if (selectedServices.indexOf('revision_bibliografica') !== -1) {
            var refCount = parseInt($('#referenceCount').val()) || 0;
            if (refCount < 1 || refCount > 300) {
                alert('⚠️ Para la revisión bibliográfica, indica una cantidad de referencias entre 1 y 300.');
                return false;
            }
        }

        // Validar nombre de revista si el cliente la sugiere
        if ($('#journalOption').val() === 'cliente') {
            var journalName = $('#journalName').val().trim();
            if (!journalName) {
                alert('⚠️ Por favor, indica el nombre de la revista sugerida.');
                return false;
            }
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
            url: '/generar-pdf/publicacion',
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
                    link.download = 'carta_compromiso_publicacion.pdf';
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
    // 10. FUNCIÓN: MOSTRAR ÉXITO Y REDIRIGIR
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
    // 11. VALIDACIONES ADICIONALES
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

    // ============================================
    // 12. INICIALIZACIÓN
    // ============================================
    setTimeout(checkSignature, 500);
    updateUI();
});