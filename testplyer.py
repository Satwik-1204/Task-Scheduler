from plyer import notification
try:
    notification.notify(
        title="Test",
        message="This is a test notification",
        app_name="TestApp",
        timeout=10
    )
    print("Test notification sent")
except Exception as e:
    print(f"Error: {str(e)}")