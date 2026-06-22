#include "PlatformGameMode.h"

#include "PlatformHostSession.h"

APlatformGameMode::APlatformGameMode()
{
    GameStateClass = APlatformHostSessionState::StaticClass();
}
