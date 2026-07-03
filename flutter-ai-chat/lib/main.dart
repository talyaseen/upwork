import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app/theme.dart';
import 'config/app_config.dart';
import 'services/ai_backend.dart';
import 'services/fastapi_backend.dart';
import 'state/chat_controller.dart';
import 'state/status_controller.dart';
import 'ui/chat_screen.dart';

void main() {
  // The one place a concrete backend is wired in. The rest of the app depends
  // only on the AiBackend interface, so switching to an OpenAiBackend (see
  // services/ai_backend.dart) is a change to this single line.
  final AiBackend backend = FastApiBackend(
    baseUrl: AppConfig.apiBaseUrl,
    username: AppConfig.demoUsername,
    password: AppConfig.demoPassword,
  );

  runApp(AiChatApp(backend: backend));
}

class AiChatApp extends StatelessWidget {
  const AiChatApp({super.key, required this.backend});

  final AiBackend backend;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Establish the transparent demo session as soon as the app starts.
        ChangeNotifierProvider(
          create: (_) => ChatController(backend)..connect(),
        ),
        // Poll the public /api/status endpoint for the site-wide banner.
        ChangeNotifierProvider(
          create: (_) =>
              StatusController.http(baseUrl: AppConfig.apiBaseUrl)..start(),
        ),
      ],
      child: MaterialApp(
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: AppTheme.build(),
        home: const ChatScreen(),
      ),
    );
  }
}
