#pragma once

#include "CoreMinimal.h"
#include "PlatformSessionTypes.generated.h"

UENUM(BlueprintType)
enum class EHostSessionState : uint8
{
    Created,
    Starting,
    Active,
    Ending,
    Ended,
    Failed
};

UENUM(BlueprintType)
enum class ELocalSlotState : uint8
{
    Empty,
    AwaitingLogin,
    Authenticated,
    Spawning,
    Active,
    Leaving,
    Disconnected,
    Released
};

UENUM(BlueprintType)
enum class EBindingState : uint8
{
    Pending,
    Active,
    Suspended,
    Ended,
    Invalidated
};

UENUM(BlueprintType)
enum class EAuditEventKind : uint8
{
    HostSessionCreated,
    HostSessionStarted,
    LocalSlotCreated,
    LoginStarted,
    LoginSucceeded,
    LoginFailed,
    UserBoundToSlot,
    PlayerControllerCreated,
    PawnSpawned,
    ViewportAssigned,
    InputAssigned,
    PlayerLeft,
    SlotReleased,
    HostSessionEnded,
    FaultDetected
};

USTRUCT(BlueprintType)
struct FPlatformUserIdentity
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString PlatformUserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString DisplayName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString AuthMethod = TEXT("mock");
};

USTRUCT(BlueprintType)
struct FLocalPlayerSlotRecord
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostSessionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString LocalSlotId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    int32 SlotIndex = INDEX_NONE;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    ELocalSlotState State = ELocalSlotState::Empty;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString InputDeviceId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString ViewportId;
};

USTRUCT(BlueprintType)
struct FUserSessionBindingRecord
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString BindingId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostSessionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString LocalSlotId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString PlatformUserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    EBindingState State = EBindingState::Pending;
};

USTRUCT(BlueprintType)
struct FSessionAuditEvent
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString AuditEventId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostSessionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    EAuditEventKind EventKind = EAuditEventKind::FaultDetected;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString PlatformUserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString LocalSlotId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString BindingId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString Summary;
};
