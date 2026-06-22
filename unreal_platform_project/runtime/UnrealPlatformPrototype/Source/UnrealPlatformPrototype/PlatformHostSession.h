#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameStateBase.h"
#include "PlatformSessionTypes.h"
#include "PlatformHostSession.generated.h"

USTRUCT(BlueprintType)
struct FHostSessionRecord
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostSessionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostDeviceId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString ExperienceVersionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    FString HostUserId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    EHostSessionState State = EHostSessionState::Created;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Platform")
    int32 MaxLocalSlots = 2;
};

UCLASS(BlueprintType)
class UNREALPLATFORMPROTOTYPE_API APlatformHostSessionState : public AGameStateBase
{
    GENERATED_BODY()

public:
    APlatformHostSessionState();

    UPROPERTY(BlueprintReadOnly, Category = "Platform")
    FHostSessionRecord HostSession;

    UPROPERTY(BlueprintReadOnly, Category = "Platform")
    TArray<FLocalPlayerSlotRecord> LocalSlots;

    UPROPERTY(BlueprintReadOnly, Category = "Platform")
    TArray<FPlatformUserIdentity> MockUsers;

    UPROPERTY(BlueprintReadOnly, Category = "Platform")
    TArray<FUserSessionBindingRecord> UserBindings;

    UPROPERTY(BlueprintReadOnly, Category = "Platform")
    TArray<FSessionAuditEvent> AuditEvents;

    UFUNCTION(BlueprintCallable, Category = "Platform")
    void CreateMockHostSession(const FString& InHostDeviceId, const FString& InExperienceVersionId);

    UFUNCTION(BlueprintCallable, Category = "Platform")
    bool CreateLocalPlayerSlot(int32 SlotIndex, FString& OutLocalSlotId);

    UFUNCTION(BlueprintCallable, Category = "Platform")
    bool MockLoginUserToSlot(const FString& LocalSlotId, const FString& PlatformUserId, const FString& DisplayName, FString& OutBindingId);

    UFUNCTION(BlueprintPure, Category = "Platform")
    bool HasIdentityCollapseFault() const;

private:
    void AppendAuditEvent(EAuditEventKind EventKind, const FString& Summary, const FString& LocalSlotId = FString(), const FString& PlatformUserId = FString(), const FString& BindingId = FString());
    FLocalPlayerSlotRecord* FindSlot(const FString& LocalSlotId);
    const FLocalPlayerSlotRecord* FindSlot(const FString& LocalSlotId) const;
    bool HasActiveUserBinding(const FString& PlatformUserId) const;
    bool HasActiveSlotBinding(const FString& LocalSlotId) const;
};
