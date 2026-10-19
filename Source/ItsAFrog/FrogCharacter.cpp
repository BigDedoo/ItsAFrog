// Fill out your copyright notice in the Description page of Project Settings.

#include "FrogCharacter.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/SkeletalMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "TongueAnimInstance.h"
#include "ItsAFrog.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	float EaseTongueAlpha(float Alpha, float Exponent)
	{
		return FMath::InterpEaseInOut(0.0f, 1.0f, FMath::Clamp(Alpha, 0.0f, 1.0f), FMath::Max(0.1f, Exponent));
	}

	FTransform MakeGuideTransform(const FVector& Location, const FVector& Direction, const FVector& Up)
	{
		const FVector SafeDirection = Direction.GetSafeNormal(KINDA_SMALL_NUMBER, FVector::ForwardVector);
		const FQuat Rotation = FRotationMatrix::MakeFromXZ(SafeDirection, Up.GetSafeNormal(KINDA_SMALL_NUMBER, FVector::UpVector)).ToQuat();
		return FTransform(Rotation, Location);
	}
}

AFrogCharacter::AFrogCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	static ConstructorHelpers::FObjectFinder<UInputAction> JumpActionAsset(TEXT("/Game/Input/Actions/IA_Jump.IA_Jump"));
	static ConstructorHelpers::FObjectFinder<UInputAction> MoveActionAsset(TEXT("/Game/Input/Actions/IA_Move.IA_Move"));
	static ConstructorHelpers::FObjectFinder<UInputAction> LookActionAsset(TEXT("/Game/Input/Actions/IA_Look.IA_Look"));
	static ConstructorHelpers::FObjectFinder<UInputAction> MouseLookActionAsset(TEXT("/Game/Input/Actions/IA_MouseLook.IA_MouseLook"));

	if (JumpActionAsset.Succeeded()) JumpAction = JumpActionAsset.Object;
	if (MoveActionAsset.Succeeded()) MoveAction = MoveActionAsset.Object;
	if (LookActionAsset.Succeeded()) LookAction = LookActionAsset.Object;
	if (MouseLookActionAsset.Succeeded()) MouseLookAction = MouseLookActionAsset.Object;

	GetCapsuleComponent()->InitCapsuleSize(42.f, 96.0f);

	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	GetCharacterMovement()->bOrientRotationToMovement = true;
	GetCharacterMovement()->RotationRate = FRotator(0.0f, 500.0f, 0.0f);
	GetCharacterMovement()->JumpZVelocity = 500.f;
	GetCharacterMovement()->AirControl = 0.35f;
	GetCharacterMovement()->MaxWalkSpeed = 500.f;
	GetCharacterMovement()->MinAnalogWalkSpeed = 20.f;
	GetCharacterMovement()->BrakingDecelerationWalking = 2000.f;
	GetCharacterMovement()->BrakingDecelerationFalling = 1500.0f;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 400.0f;
	CameraBoom->bUsePawnControlRotation = true;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	TongueMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("TongueMesh"));
	TongueMesh->SetupAttachment(GetMesh(), TongueSocketName);
	TongueMesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	TongueMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	TongueMesh->SetGenerateOverlapEvents(false);
	TongueMesh->SetSimulatePhysics(false);
	TongueMesh->SetVisibility(false, true);
	TongueMesh->SetComponentTickEnabled(false);
}

void AFrogCharacter::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	ApplyStylizedMesh();
	ApplyCameraMode();
}

void AFrogCharacter::BeginPlay()
{
	Super::BeginPlay();

	ApplyStylizedMesh();
	ApplyCameraMode();
	ValidateTongueConfiguration();
	if (GetMesh() && GetMesh()->DoesSocketExist(TongueSocketName))
	{
		TongueMesh->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, TongueSocketName);
	}
}

void AFrogCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (bUseDioramaCamera && CameraBoom)
	{
		CameraBoom->TargetArmLength = FMath::FInterpTo(CameraBoom->TargetArmLength, DioramaArmLength, DeltaTime, DioramaZoomSpeed);
	}
	TickLocomotion();
	TickTongue(DeltaTime);
}

void AFrogCharacter::ApplyCameraMode()
{
	if (!CameraBoom || !FollowCamera || !bUseDioramaCamera)
	{
		return;
	}

	CameraBoom->bUsePawnControlRotation = false;
	CameraBoom->bInheritPitch = false;
	CameraBoom->bInheritYaw = false;
	CameraBoom->bInheritRoll = false;
	CameraBoom->bDoCollisionTest = false;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 8.0f;
	CameraBoom->TargetArmLength = DioramaArmLength;
	CameraBoom->SetUsingAbsoluteRotation(true);
	CameraBoom->SetWorldRotation(FRotator(DioramaPitch, DioramaYaw, 0.0f));
	FollowCamera->SetFieldOfView(DioramaFieldOfView);
}

void AFrogCharacter::ApplyStylizedMesh()
{
	USkeletalMeshComponent* MeshComponent = GetMesh();
	if (!StylizedMesh || !MeshComponent)
	{
		return;
	}

	if (MeshComponent->GetSkeletalMeshAsset() != StylizedMesh)
	{
		MeshComponent->SetSkeletalMeshAsset(StylizedMesh);
		CurrentLocomotionAnimation = nullptr;
	}

	// Fit the capsule to the mesh; the mesh origin is at the feet.
	const FBoxSphereBounds Bounds = StylizedMesh->GetBounds();
	const float MeshHeight = static_cast<float>(Bounds.Origin.Z + Bounds.BoxExtent.Z);
	const float MeshHalfWidth = static_cast<float>(FMath::Min(Bounds.BoxExtent.X, Bounds.BoxExtent.Y));
	const float HalfHeight = FMath::Max(StylizedCapsuleHeight > 0.0f ? StylizedCapsuleHeight : MeshHeight, 20.0f) * 0.5f;
	const float Radius = FMath::Clamp(StylizedCapsuleRadius > 0.0f ? StylizedCapsuleRadius : MeshHalfWidth * 0.8f, 10.0f, HalfHeight);
	GetCapsuleComponent()->SetCapsuleSize(Radius, HalfHeight);
	MeshComponent->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, -HalfHeight), FRotator(0.0f, StylizedMeshYaw, 0.0f));
}

void AFrogCharacter::TickLocomotion()
{
	USkeletalMeshComponent* MeshComponent = GetMesh();
	if (!WalkAnimation || !MeshComponent || MeshComponent->GetAnimClass())
	{
		return;
	}

	const float Speed = GetVelocity().Size2D();
	UAnimSequence* Desired = WalkAnimation;
	if (Speed < 10.0f && IdleAnimation)
	{
		Desired = IdleAnimation;
	}
	else if (Speed > RunSpeedThreshold && RunAnimation)
	{
		Desired = RunAnimation;
	}

	if (Desired != CurrentLocomotionAnimation)
	{
		MeshComponent->PlayAnimation(Desired, true);
		CurrentLocomotionAnimation = Desired;
	}
}

FRotator AFrogCharacter::GetMovementBasis() const
{
	if (bUseDioramaCamera && CameraBoom)
	{
		return FRotator(0.0f, CameraBoom->GetComponentRotation().Yaw, 0.0f);
	}
	return GetController() ? FRotator(0.0f, GetController()->GetControlRotation().Yaw, 0.0f) : FRotator::ZeroRotator;
}

void AFrogCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	if (UEnhancedInputComponent* EnhancedInputComponent = Cast<UEnhancedInputComponent>(PlayerInputComponent))
	{
		EnhancedInputComponent->BindAction(JumpAction, ETriggerEvent::Started, this, &AFrogCharacter::DoJumpStart);
		EnhancedInputComponent->BindAction(JumpAction, ETriggerEvent::Completed, this, &AFrogCharacter::DoJumpEnd);
		EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AFrogCharacter::Move);
		EnhancedInputComponent->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &AFrogCharacter::Look);
		EnhancedInputComponent->BindAction(LookAction, ETriggerEvent::Triggered, this, &AFrogCharacter::Look);

		EnsureZoomInput();
		EnhancedInputComponent->BindAction(ZoomAction, ETriggerEvent::Triggered, this, &AFrogCharacter::Zoom);

		if (TongueAction)
		{
			EnhancedInputComponent->BindAction(TongueAction, ETriggerEvent::Started, this, &AFrogCharacter::HandleTongueStarted);
			EnhancedInputComponent->BindAction(TongueAction, ETriggerEvent::Completed, this, &AFrogCharacter::HandleTongueCompleted);
			EnhancedInputComponent->BindAction(TongueAction, ETriggerEvent::Canceled, this, &AFrogCharacter::HandleTongueCanceled);
		}
		else
		{
			UE_LOG(LogItsAFrog, Warning, TEXT("'%s' has no TongueAction assigned; tongue input is disabled."), *GetNameSafe(this));
		}
	}
	else
	{
		UE_LOG(LogItsAFrog, Error, TEXT("'%s' requires an Enhanced Input component."), *GetNameSafe(this));
	}
}

void AFrogCharacter::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();

	if (const APlayerController* PlayerController = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PlayerController->GetLocalPlayer()))
		{
			EnsureZoomInput();
			Subsystem->AddMappingContext(ZoomMappingContext, 1);
		}
	}
}

void AFrogCharacter::EnsureZoomInput()
{
	if (ZoomMappingContext)
	{
		return;
	}

	if (!ZoomAction)
	{
		ZoomAction = NewObject<UInputAction>(this, TEXT("IA_DioramaZoom"));
		ZoomAction->ValueType = EInputActionValueType::Axis1D;
	}

	// The wheel reports one unit per notch; held shoulders are scaled to about eight notches a second.
	ZoomMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_DioramaZoom"));
	ZoomMappingContext->MapKey(ZoomAction, EKeys::MouseWheelAxis);
	for (const FKey& Key : { EKeys::Gamepad_RightShoulder, EKeys::Gamepad_LeftShoulder })
	{
		FEnhancedActionKeyMapping& Mapping = ZoomMappingContext->MapKey(ZoomAction, Key);
		Mapping.Modifiers.Add(NewObject<UInputModifierScaleByDeltaTime>(ZoomMappingContext));
		UInputModifierScalar* Rate = NewObject<UInputModifierScalar>(ZoomMappingContext);
		Rate->Scalar = FVector(Key == EKeys::Gamepad_LeftShoulder ? -8.0 : 8.0);
		Mapping.Modifiers.Add(Rate);
	}
}

void AFrogCharacter::Move(const FInputActionValue& Value)
{
	const FVector2D MovementVector = Value.Get<FVector2D>();
	DoMove(MovementVector.X, MovementVector.Y);
}

void AFrogCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D LookAxisVector = Value.Get<FVector2D>();
	DoLook(LookAxisVector.X, LookAxisVector.Y);
}

void AFrogCharacter::Zoom(const FInputActionValue& Value)
{
	DoZoom(Value.Get<float>());
}

void AFrogCharacter::DoZoom(float Amount)
{
	if (bUseDioramaCamera)
	{
		const float Closest = FMath::Min(DioramaMinArmLength, DioramaMaxArmLength);
		const float Farthest = FMath::Max(DioramaMinArmLength, DioramaMaxArmLength);
		DioramaArmLength = FMath::Clamp(DioramaArmLength - Amount * DioramaZoomStep, Closest, Farthest);
	}
}

void AFrogCharacter::DoMove(float Right, float Forward)
{
	if (GetController() != nullptr)
	{
		const FRotator YawRotation = GetMovementBasis();
		const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
		const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

		AddMovementInput(ForwardDirection, Forward);
		AddMovementInput(RightDirection, Right);
	}
}

void AFrogCharacter::DoLook(float Yaw, float Pitch)
{
	if (bUseDioramaCamera)
	{
		if (CameraBoom)
		{
			// Same sense as the orbit camera's AddControllerPitchInput: positive tilts towards the horizon.
			const float Steepest = FMath::Min(DioramaMinPitch, DioramaMaxPitch);
			const float Flattest = FMath::Max(DioramaMinPitch, DioramaMaxPitch);
			DioramaYaw = FMath::UnwindDegrees(DioramaYaw + Yaw * DioramaTurnScale);
			DioramaPitch = FMath::Clamp(DioramaPitch + Pitch * DioramaTiltScale, Steepest, Flattest);
			CameraBoom->SetWorldRotation(FRotator(DioramaPitch, DioramaYaw, 0.0f));
		}
		return;
	}

	if (GetController() != nullptr)
	{
		AddControllerYawInput(Yaw);
		AddControllerPitchInput(Pitch);
	}
}

void AFrogCharacter::DoJumpStart()
{
	Jump();
}

void AFrogCharacter::DoJumpEnd()
{
	StopJumping();
}

void AFrogCharacter::HandleTongueStarted()
{
	LaunchTongue();
}

void AFrogCharacter::HandleTongueCompleted()
{
	ReleaseTongue();
}

void AFrogCharacter::HandleTongueCanceled()
{
	ReleaseTongue();
}

void AFrogCharacter::LaunchTongue()
{
	if (TongueState != ETongueState::Hidden)
	{
		return;
	}

	ValidateTongueConfiguration();

	FVector MouthLocation;
	if (!TryGetMouthLocation(MouthLocation))
	{
		return;
	}

	UTongueAnimInstance* TongueAnimInstance = nullptr;
	if (!TongueMesh || !TongueMesh->GetSkeletalMeshAsset() || !TryGetTongueAnimInstance(TongueAnimInstance))
	{
		return;
	}

	// The diorama camera looks down at the frog, so aim along the frog's facing instead.
	const FVector AimDirection = bUseDioramaCamera
		? GetActorForwardVector()
		: FollowCamera
		? FollowCamera->GetForwardVector().GetSafeNormal()
		: (GetController() ? GetController()->GetControlRotation().Vector().GetSafeNormal() : FVector::ZeroVector);
	if (AimDirection.IsNearlyZero())
	{
		UE_LOG(LogItsAFrog, Warning, TEXT("'%s' could not determine a tongue aim direction."), *GetNameSafe(this));
		return;
	}

	const FVector TraceEnd = MouthLocation + AimDirection * MaximumTongueLength;
	TongueEndpoint = TraceEnd;
	TongueTargetActor = nullptr;
	TongueTargetComponent = nullptr;
	TongueTargetPointLocal = FVector::ZeroVector;

	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(TongueTrace), false, this);
	QueryParams.AddIgnoredActor(this);

	FHitResult HitResult;
	const bool bHit = GetWorld() && GetWorld()->SweepSingleByChannel(
		HitResult,
		MouthLocation,
		TraceEnd,
		FQuat::Identity,
		TongueTraceChannel,
		FCollisionShape::MakeSphere(TraceRadius),
		QueryParams);

	if (bHit && HitResult.GetComponent())
	{
		TongueEndpoint = HitResult.ImpactPoint;
		TongueTargetActor = HitResult.GetActor();
		TongueTargetComponent = HitResult.GetComponent();
		TongueTargetPointLocal = TongueTargetComponent->GetComponentTransform().InverseTransformPosition(TongueEndpoint);
	}

	RetractionStartEndpoint = TongueEndpoint;
	if (!SetTongueState(ETongueState::Extending))
	{
		return;
	}

	TongueMesh->SetVisibility(true, true);
	TongueMesh->SetComponentTickEnabled(true);
	UpdateTonguePose(MouthLocation, MouthLocation, 0.0f);
	DrawTongueDebug(MouthLocation, TongueEndpoint);
}

void AFrogCharacter::ReleaseTongue()
{
	if (TongueState == ETongueState::Extending || TongueState == ETongueState::Attached)
	{
		BeginTongueRetraction();
	}
}

void AFrogCharacter::TickTongue(float DeltaTime)
{
	if (TongueState == ETongueState::Hidden)
	{
		return;
	}

	TongueStateTime += FMath::Max(0.0f, DeltaTime);

	if (TongueState == ETongueState::Cooldown)
	{
		if (TongueStateTime >= CooldownDuration)
		{
			SetTongueState(ETongueState::Hidden);
		}
		return;
	}

	FVector MouthLocation;
	if (!TryGetMouthLocation(MouthLocation))
	{
		BeginTongueRetraction();
		return;
	}

	if (TongueState == ETongueState::Extending)
	{
		if (TongueTargetComponent)
		{
			if (!IsValid(TongueTargetComponent))
			{
				BeginTongueRetraction();
				return;
			}
			TongueEndpoint = TongueTargetComponent->GetComponentTransform().TransformPosition(TongueTargetPointLocal);
		}

		const float LinearAlpha = TongueStateTime / FMath::Max(ExtensionDuration, KINDA_SMALL_NUMBER);
		const float ExtensionAlpha = EaseTongueAlpha(LinearAlpha, EasingExponent);
		const FVector TipLocation = FMath::Lerp(MouthLocation, TongueEndpoint, ExtensionAlpha);
		UpdateTonguePose(MouthLocation, TipLocation, ExtensionAlpha);

		if (LinearAlpha >= 1.0f)
		{
			if (TongueTargetComponent && IsValid(TongueTargetComponent))
			{
				SetTongueState(ETongueState::Attached);
			}
			else
			{
				BeginTongueRetraction();
			}
		}
	}
	else if (TongueState == ETongueState::Attached)
	{
		if (!TongueTargetComponent || !IsValid(TongueTargetComponent))
		{
			BeginTongueRetraction();
			return;
		}

		TongueEndpoint = TongueTargetComponent->GetComponentTransform().TransformPosition(TongueTargetPointLocal);
		UpdateTongueAttachment();
		UpdateTonguePose(MouthLocation, TongueEndpoint, 1.0f);

		if (TongueStateTime >= MaximumAttachedDuration)
		{
			BeginTongueRetraction();
		}
	}
	else if (TongueState == ETongueState::Retracting)
	{
		const float LinearAlpha = TongueStateTime / FMath::Max(RetractionDuration, KINDA_SMALL_NUMBER);
		const float RetractionAlpha = EaseTongueAlpha(LinearAlpha, EasingExponent);
		const FVector TipLocation = FMath::Lerp(RetractionStartEndpoint, MouthLocation, RetractionAlpha);
		UpdateTonguePose(MouthLocation, TipLocation, 1.0f - RetractionAlpha);

		if (LinearAlpha >= 1.0f)
		{
			CompleteTongueRetraction();
		}
	}
}

bool AFrogCharacter::SetTongueState(ETongueState NewState)
{
	if (TongueState == NewState)
	{
		return true;
	}

	if (!CanTransitionTongueState(TongueState, NewState))
	{
		UE_LOG(LogItsAFrog, Warning, TEXT("Rejected tongue state transition %d -> %d on '%s'."), static_cast<int32>(TongueState), static_cast<int32>(NewState), *GetNameSafe(this));
		return false;
	}

	TongueState = NewState;
	TongueStateTime = 0.0f;

	if (NewState == ETongueState::Attached)
	{
		OnTongueAttached();
	}
	else if (NewState == ETongueState::Retracting)
	{
		RetractionStartEndpoint = TongueEndpoint;
		OnTongueReleased();
	}

	return true;
}

bool AFrogCharacter::CanTransitionTongueState(ETongueState From, ETongueState To) const
{
	switch (From)
	{
	case ETongueState::Hidden:
		return To == ETongueState::Extending;
	case ETongueState::Extending:
		return To == ETongueState::Attached || To == ETongueState::Retracting;
	case ETongueState::Attached:
		return To == ETongueState::Retracting;
	case ETongueState::Retracting:
		return To == ETongueState::Cooldown;
	case ETongueState::Cooldown:
		return To == ETongueState::Hidden;
	default:
		return false;
	}
}

bool AFrogCharacter::TryGetTongueAnimInstance(UTongueAnimInstance*& OutAnimInstance)
{
	OutAnimInstance = nullptr;
	if (!TongueMesh)
	{
		return false;
	}

	OutAnimInstance = Cast<UTongueAnimInstance>(TongueMesh->GetAnimInstance());
	if (!OutAnimInstance && !bWarnedMissingAnimInstance)
	{
		bWarnedMissingAnimInstance = true;
		UE_LOG(LogItsAFrog, Warning, TEXT("'%s' TongueMesh has no UTongueAnimInstance-compatible Animation Blueprint assigned."), *GetNameSafe(this));
	}
	return OutAnimInstance != nullptr;
}

bool AFrogCharacter::TryGetMouthLocation(FVector& OutLocation) const
{
	if (GetMesh() && GetMesh()->DoesSocketExist(TongueSocketName))
	{
		OutLocation = GetMesh()->GetSocketLocation(TongueSocketName);
		return true;
	}

	if (!bWarnedMissingSocket)
	{
		const_cast<AFrogCharacter*>(this)->bWarnedMissingSocket = true;
		UE_LOG(LogItsAFrog, Warning, TEXT("'%s' frog mesh is missing tongue socket '%s'."), *GetNameSafe(this), *TongueSocketName.ToString());
	}
	return false;
}

void AFrogCharacter::UpdateTonguePose(const FVector& RootLocation, const FVector& TipLocation, float ExtensionAlpha)
{
	UTongueAnimInstance* TongueAnimInstance = nullptr;
	if (!TongueMesh || !TryGetTongueAnimInstance(TongueAnimInstance))
	{
		return;
	}

	const FVector UpDirection = GetActorUpVector();
	const FVector RightDirection = GetActorRightVector();
	const FVector RootToTip = TipLocation - RootLocation;
	const float ArcScale = FMath::Clamp(ExtensionAlpha, 0.0f, 1.0f);

	const FVector MidALocation = FMath::Lerp(RootLocation, TipLocation, 1.0f / 3.0f)
		+ UpDirection * (ArcHeight * ArcScale)
		+ RightDirection * (SideArcOffset * ArcScale);
	const FVector MidBLocation = FMath::Lerp(RootLocation, TipLocation, 2.0f / 3.0f)
		+ UpDirection * (ArcHeight * 0.5f * ArcScale)
		+ RightDirection * (SideArcOffset * 0.5f * ArcScale);

		const FTransform RootGuide = MakeGuideTransform(RootLocation, RootToTip, UpDirection);
		const FTransform MidAGuide = MakeGuideTransform(MidALocation, RootToTip, UpDirection);
		const FTransform MidBGuide = MakeGuideTransform(MidBLocation, RootToTip, UpDirection);
		const FTransform TipGuide = MakeGuideTransform(TipLocation, RootToTip, UpDirection);

	const FTransform ComponentTransform = TongueMesh->GetComponentTransform();
	auto ToComponentSpace = [&ComponentTransform](const FTransform& WorldTransform)
	{
		FTransform ComponentSpaceTransform = WorldTransform;
		ComponentSpaceTransform.SetLocation(ComponentTransform.InverseTransformPosition(WorldTransform.GetLocation()));
		ComponentSpaceTransform.SetRotation(ComponentTransform.InverseTransformRotation(WorldTransform.GetRotation()));
		return ComponentSpaceTransform;
	};

	FTonguePoseData Pose;
	Pose.RootGuide = ToComponentSpace(RootGuide);
	Pose.MidAGuide = ToComponentSpace(MidAGuide);
	Pose.MidBGuide = ToComponentSpace(MidBGuide);
	Pose.TipGuide = ToComponentSpace(TipGuide);
	Pose.bTongueActive = true;
	Pose.ExtensionAlpha = FMath::Clamp(ExtensionAlpha, 0.0f, 1.0f);
	TongueAnimInstance->SetTonguePose(Pose);

	DrawTongueDebug(RootLocation, TipLocation);
	if (bDrawTongueDebug && GetWorld())
	{
		const float Lifetime = FMath::Max(0.0f, DebugDrawDuration);
		DrawDebugSphere(GetWorld(), MidALocation, 5.0f, 8, FColor::Orange, false, Lifetime);
		DrawDebugSphere(GetWorld(), MidBLocation, 5.0f, 8, FColor::Orange, false, Lifetime);
		DrawDebugLine(GetWorld(), RootLocation, MidALocation, FColor::Orange, false, Lifetime, 0, 1.0f);
		DrawDebugLine(GetWorld(), MidALocation, MidBLocation, FColor::Orange, false, Lifetime, 0, 1.0f);
		DrawDebugLine(GetWorld(), MidBLocation, TipLocation, FColor::Orange, false, Lifetime, 0, 1.0f);
		DrawDebugString(GetWorld(), TipLocation, StaticEnum<ETongueState>()->GetNameStringByValue(static_cast<int64>(TongueState)), nullptr, FColor::White, Lifetime, false);
	}
}

void AFrogCharacter::BeginTongueRetraction()
{
	if (TongueState == ETongueState::Extending || TongueState == ETongueState::Attached)
	{
		SetTongueState(ETongueState::Retracting);
	}
}

void AFrogCharacter::CompleteTongueRetraction()
{
	TongueTargetActor = nullptr;
	TongueTargetComponent = nullptr;
	TongueTargetPointLocal = FVector::ZeroVector;
	TongueEndpoint = FVector::ZeroVector;
	RetractionStartEndpoint = FVector::ZeroVector;

	if (TongueMesh)
	{
		TongueMesh->SetVisibility(false, true);
		TongueMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		TongueMesh->SetComponentTickEnabled(false);
	}

	if (UTongueAnimInstance* TongueAnimInstance = TongueMesh ? Cast<UTongueAnimInstance>(TongueMesh->GetAnimInstance()) : nullptr)
	{
		TongueAnimInstance->SetTonguePose(FTonguePoseData());
	}

	SetTongueState(ETongueState::Cooldown);
}

void AFrogCharacter::ValidateTongueConfiguration()
{
	bool bInvalid = false;
	if (MaximumTongueLength <= 0.0f)
	{
		MaximumTongueLength = 500.0f;
		bInvalid = true;
	}
	if (TraceRadius < 0.0f)
	{
		TraceRadius = 0.0f;
		bInvalid = true;
	}
	if (ExtensionDuration <= 0.0f)
	{
		ExtensionDuration = 0.12f;
		bInvalid = true;
	}
	if (RetractionDuration <= 0.0f)
	{
		RetractionDuration = 0.18f;
		bInvalid = true;
	}
	if (MaximumAttachedDuration < 0.0f || CooldownDuration < 0.0f || EasingExponent <= 0.0f)
	{
		MaximumAttachedDuration = FMath::Max(0.0f, MaximumAttachedDuration);
		CooldownDuration = FMath::Max(0.0f, CooldownDuration);
		EasingExponent = FMath::Max(0.1f, EasingExponent);
		bInvalid = true;
	}

	if (bInvalid && !bWarnedInvalidConfiguration)
	{
		bWarnedInvalidConfiguration = true;
		UE_LOG(LogItsAFrog, Warning, TEXT("Invalid tongue configuration on '%s'; invalid values were corrected."), *GetNameSafe(this));
	}

	if (TongueMesh && !TongueMesh->GetSkeletalMeshAsset() && !bWarnedMissingTongueMeshAsset)
	{
		bWarnedMissingTongueMeshAsset = true;
		UE_LOG(LogItsAFrog, Warning, TEXT("'%s' TongueMesh has no Skeletal Mesh assigned."), *GetNameSafe(this));
	}
}

void AFrogCharacter::DrawTongueDebug(const FVector& RootLocation, const FVector& TipLocation) const
{
	if (!bDrawTongueDebug || !GetWorld())
	{
		return;
	}

	const float Lifetime = FMath::Max(0.0f, DebugDrawDuration);
	DrawDebugLine(GetWorld(), RootLocation, RootLocation + (TipLocation - RootLocation).GetSafeNormal() * MaximumTongueLength, FColor::Yellow, false, Lifetime, 0, 1.0f);
	DrawDebugSphere(GetWorld(), RootLocation, TraceRadius, 12, FColor::Green, false, Lifetime);
	DrawDebugSphere(GetWorld(), TipLocation, TraceRadius, 12, TongueTargetComponent ? FColor::Red : FColor::Cyan, false, Lifetime);
	DrawDebugLine(GetWorld(), RootLocation, TipLocation, TongueTargetComponent ? FColor::Red : FColor::Cyan, false, Lifetime, 0, 3.0f);
}

void AFrogCharacter::OnTongueAttached()
{
	// Extension point for future authority checks, pulling, or grappling.
}

void AFrogCharacter::UpdateTongueAttachment()
{
	// Extension point for future target interaction. No pulling is implemented.
}

void AFrogCharacter::OnTongueReleased()
{
	// Extension point for future release effects or replicated state changes.
}
