import 'package:flutter/widgets.dart';
import 'package:flutter_map/flutter_map.dart';

import '../../nucleo/configuracion.dart';

const agenteUsuarioMapa = 'com.busetasapp.prototipo';

/// Teselas de OpenStreetMap (URL en `MAP_TILE_URL`) y atribución siempre visible.
List<Widget> capasBaseOsm() => [
      TileLayer(
        urlTemplate: Configuracion.mapTileUrl,
        userAgentPackageName: agenteUsuarioMapa,
      ),
      const SimpleAttributionWidget(source: Text('© OpenStreetMap contributors')),
    ];
