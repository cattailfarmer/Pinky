#include "PlatformHostSession.h"

#include "Misc/Guid.h"

APlatformHostSessionState::APlatformHostSessionState()
{
    HostSession.MaxLocalSlots = 2;
}

void APlatformHostSessionState::CreateMockHostSession(const FString& InHostDeviceId, const FString& InExperienceVersionId)
{
    HostSession.HostSessionId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
    HostSession.HostDeviceId = InHostDeviceId;
    HostSession.ExperienceVersionId = InExperienceVersionId;
    HostSession.State = EHostSessionState::Active;
    HostSession.MaxLocalSlots = 2;

    LocalSlots.Reset();
    MockUsers.Reset();
    UserBindings.Reset();
    AuditEvents.Reset();

    AppendAuditEvent(EAuditEventKind::HostSessionCreated, TEXT("Mock host session created."));
    AppendAuditEvent(EAuditEventKind::HostSessionStarted, TEXT("Mock host session started."));
}

bool APlatformHostSessionState::CreateLocalPlayerSlot(int32 SlotIndex, FString& OutLocalSlotId)
{
    OutLocalSlotId.Reset();

    if (HostSession.HostSessionId.IsEmpty() || LocalSlots.Num() >= HostSession.MaxLocalSlots)
    {
        AppendAuditEvent(EAuditEventKind::FaultDetected, TEXT("Local slot creation rejected."));
        return false;
    }

    FLocalPlayerSlotRecord Slot;
    Slot.HostSessionId = HostSession.HostSessionId;
    Slot.LocalSlotId = FString::Printf(TEXT("%s-slot-%d"), *HostSession.HostSessionId, SlotIndex);
    Slot.SlotIndex = SlotIndex;
    Slot.State = ELocalSlotState::AwaitingLogin;

    OutLocalSlotId = Slot.LocalSlotId;
    LocalSlots.Add(Slot);

    AppendAuditEvent(EAuditEventKind::LocalSlotCreated, TEXT("Local player slot created."), Slot.LocalSlotId);
    return true;
}

bool APlatformHostSessionState::MockLoginUserToSlot(const FString& LocalSlotId, const FString& PlatformUserId, const FString& DisplayName, FString& OutBindingId)
{
    OutBindingId.Reset();

    FLocalPlayerSlotRecord* Slot = FindSlot(LocalSlotId);
    if (!Slot || PlatformUserId.IsEmpty() || HasActiveUserBinding(PlatformUserId) || HasActiveSlotBinding(LocalSlotId))
    {
        AppendAuditEvent(EAuditEventKind::LoginFailed, TEXT("Mock login rejected."), LocalSlotId, PlatformUserId);
        return false;
    }

    FPlatformUserIdentity User;
    User.PlatformUserId = PlatformUserId;
    User.DisplayName = DisplayName;
    User.AuthMethod = TEXT("mock");
    MockUsers.Add(User);

    FUserSessionBindingRecord Binding;
    Binding.BindingId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
    Binding.HostSessionId = HostSession.HostSessionId;
    Binding.LocalSlotId = LocalSlotId;
    Binding.PlatformUserId = PlatformUserId;
    Binding.State = EBindingState::Active;
    UserBindings.Add(Binding);

    Slot->State = ELocalSlotState::Authenticated;
    OutBindingId = Binding.BindingId;

    AppendAuditEvent(EAuditEventKind::LoginSucceeded, TEXT("Mock user authenticated."), LocalSlotId, PlatformUserId);
    AppendAuditEvent(EAuditEventKind::UserBoundToSlot, TEXT("User bound to local slot."), LocalSlotId, PlatformUserId, Binding.BindingId);
    return true;
}

bool APlatformHostSessionState::HasIdentityCollapseFault() const
{
    for (const FUserSessionBindingRecord& Binding : UserBindings)
    {
        if (Binding.PlatformUserId.IsEmpty() || Binding.LocalSlotId.IsEmpty() || Binding.PlatformUserId == Binding.LocalSlotId)
        {
            return true;
        }

        const FLocalPlayerSlotRecord* Slot = FindSlot(Binding.LocalSlotId);
        if (!Slot || Slot->HostSessionId != Binding.HostSessionId)
        {
            return true;
        }
    }

    return false;
}

void APlatformHostSessionState::AppendAuditEvent(EAuditEventKind EventKind, const FString& Summary, const FString& LocalSlotId, const FString& PlatformUserId, const FString& BindingId)
{
    FSessionAuditEvent Event;
    Event.AuditEventId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
    Event.HostSessionId = HostSession.HostSessionId;
    Event.EventKind = EventKind;
    Event.PlatformUserId = PlatformUserId;
    Event.LocalSlotId = LocalSlotId;
    Event.BindingId = BindingId;
    Event.Summary = Summary;
    AuditEvents.Add(Event);
}

FLocalPlayerSlotRecord* APlatformHostSessionState::FindSlot(const FString& LocalSlotId)
{
    return LocalSlots.FindByPredicate([&LocalSlotId](const FLocalPlayerSlotRecord& Slot)
    {
        return Slot.LocalSlotId == LocalSlotId;
    });
}

const FLocalPlayerSlotRecord* APlatformHostSessionState::FindSlot(const FString& LocalSlotId) const
{
    return LocalSlots.FindByPredicate([&LocalSlotId](const FLocalPlayerSlotRecord& Slot)
    {
        return Slot.LocalSlotId == LocalSlotId;
    });
}

bool APlatformHostSessionState::HasActiveUserBinding(const FString& PlatformUserId) const
{
    return UserBindings.ContainsByPredicate([&PlatformUserId](const FUserSessionBindingRecord& Binding)
    {
        return Binding.PlatformUserId == PlatformUserId && Binding.State == EBindingState::Active;
    });
}

bool APlatformHostSessionState::HasActiveSlotBinding(const FString& LocalSlotId) const
{
    return UserBindings.ContainsByPredicate([&LocalSlotId](const FUserSessionBindingRecord& Binding)
    {
        return Binding.LocalSlotId == LocalSlotId && Binding.State == EBindingState::Active;
    });
}
