import numpy as np

from common.protocol import (
    MessageType,
    WireMessage,
    decode_daq_data,
    decode_message,
    encode_message,
    make_daq_data_message,
)


def test_control_message_round_trip() -> None:
    original = WireMessage(
        MessageType.START_SESSION,
        {"test_name": "KNSB_001"},
        request_id="request-1",
    )
    decoded = decode_message(encode_message(original))

    assert decoded == original


def test_binary_daq_message_round_trip() -> None:
    values = np.array([[1.5, 2.5], [3.5, 4.5]], dtype=np.float32)
    message = make_daq_data_message(
        sequence=7,
        first_sample_index=100,
        sample_rate=5000,
        channel_names=("thrust_N", "pressure_bar"),
        values=values,
    )
    decoded = decode_daq_data(decode_message(encode_message(message)))

    assert decoded.sequence == 7
    assert decoded.first_sample_index == 100
    assert decoded.sample_rate == 5000
    np.testing.assert_allclose(decoded.values, values)
