// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Mark Ivanovskyy

#include "nexarch.h"

#include <QCheckBox>
#include <QComboBox>
#include <QCoreApplication>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QJsonArray>
#include <QJsonDocument>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QPushButton>
#include <QRandomGenerator>
#include <QSettings>
#include <QSlider>
#include <QTableWidget>
#include <QTextBrowser>
#include <QTextStream>
#include <QUrlQuery>
#include <QUuid>
#include <QVBoxLayout>

#include <board/board.h>
#include <board/boardfactory.h>
#include <board/move.h>
#include <board/piece.h>
#include <board/westernboard.h>
#include <board/result.h>
#include <pgngame.h>
#include <engineconfiguration.h>
#include <enginemanager.h>
#include "cutechessapp.h"


namespace
{
QString uciFromGeneric(const Chess::GenericMove& move)
{
	if (move.isNull())
		return QString();
	QChar file = QChar('a' + move.sourceSquare().file());
	QChar rank = QChar('1' + move.sourceSquare().rank());
	QString uci = QString() + file + rank;
	file = QChar('a' + move.targetSquare().file());
	rank = QChar('1' + move.targetSquare().rank());
	uci += QString() + file + rank;
	if (move.promotion() > 0)
	{
		QChar piece('q');
		switch (move.promotion())
		{
		case Chess::WesternBoard::Knight: piece = 'n'; break;
		case Chess::WesternBoard::Bishop: piece = 'b'; break;
		case Chess::WesternBoard::Rook: piece = 'r'; break;
		default: break;
		}
		uci += piece;
	}
	return uci;
}

QJsonObject replyJson(QNetworkReply* reply)
{
	QByteArray data = reply->readAll();
	QJsonParseError error;
	QJsonDocument doc = QJsonDocument::fromJson(data, &error);
	if (error.error != QJsonParseError::NoError || !doc.isObject())
		return QJsonObject();
	return doc.object();
}

QString errorText(QNetworkReply* reply, const QJsonObject& obj)
{
	if (obj.contains("error"))
		return obj.value("error").toString();
	if (reply->error() != QNetworkReply::NoError)
		return reply->errorString();
	return QString();
}
}

RemotePlayer::RemotePlayer(QObject* parent)
	: ChessPlayer(parent)
{
	setState(Idle);
	setName("Opponent");
}

void RemotePlayer::startGame()
{
	m_buffer = Chess::Move();
}

void RemotePlayer::startThinking()
{
	if (m_buffer.isNull())
		return;
	Chess::Move move = m_buffer;
	m_buffer = Chess::Move();
	if (board() != nullptr && board()->isLegalMove(move))
		emitMove(move);
}

void RemotePlayer::endGame(const Chess::Result& result)
{
	m_buffer = Chess::Move();
	ChessPlayer::endGame(result);
	setState(Idle);
}

void RemotePlayer::makeMove(const Chess::Move& move)
{
	Q_UNUSED(move);
}

bool RemotePlayer::supportsVariant(const QString& variant) const
{
	Q_UNUSED(variant);
	return true;
}

bool RemotePlayer::isHuman() const
{
	return false;
}

void RemotePlayer::receiveMove(const QString& uci)
{
	if (board() == nullptr || uci.isEmpty())
		return;
	if (state() != Thinking && state() != Observing)
		return;
	Chess::Move move = board()->moveFromString(uci);
	if (move.isNull() || !board()->isLegalMove(move))
		return;
	if (board()->sideToMove() != side())
		return;
	if (state() != Thinking)
	{
		m_buffer = move;
		return;
	}
	emitMove(move);
}

void RemotePlayer::receiveMoves(const QStringList& moves)
{
	for (const QString& move : moves)
		receiveMove(move);
}

RemoteBuilder::RemoteBuilder(const QString& name)
	: PlayerBuilder(name)
{
}

bool RemoteBuilder::isHuman() const
{
	return false;
}

ChessPlayer* RemoteBuilder::create(QObject* receiver,
				   const char* method,
				   QObject* parent,
				   QString* error) const
{
	Q_UNUSED(receiver);
	Q_UNUSED(method);
	Q_UNUSED(error);
	auto player = new RemotePlayer(parent);
	player->setName(name());
	return player;
}

NexarchOnline::NexarchOnline(QObject* parent)
	: QObject(parent),
	  m_count(0),
	  m_polling(false)
{
	m_timer.setInterval(1000);
	connect(&m_timer, &QTimer::timeout, this, &NexarchOnline::poll);
}

QString NexarchOnline::base() const
{
	QString url = m_server.trimmed();
	while (url.endsWith('/'))
		url.chop(1);
	return url;
}

QString NexarchOnline::server() const { return m_server; }
QString NexarchOnline::room() const { return m_room; }
QString NexarchOnline::token() const { return m_token; }
QString NexarchOnline::color() const { return m_color; }
QString NexarchOnline::playerName() const { return m_name; }
QString NexarchOnline::opponentName() const { return m_opponent.isEmpty() ? tr("Opponent") : m_opponent; }
QStringList NexarchOnline::initialMoves() const { return m_initialMoves; }
int NexarchOnline::initialCount() const { return m_count; }

void NexarchOnline::createRoom(const QString& server, const QString& name, const QString& color)
{
	m_server = server;
	m_name = name.isEmpty() ? tr("Player") : name;
	m_color = color;
	if (m_color == "r")
		m_color = (QRandomGenerator::global()->bounded(2) == 0) ? "w" : "b";
	QJsonObject body;
	body["name"] = m_name;
	body["color"] = m_color;
	post("/api/room", body, SLOT(handleRoom()));
}

void NexarchOnline::joinRoom(const QString& server, const QString& name, const QString& room)
{
	m_server = server;
	m_name = name.isEmpty() ? tr("Player") : name;
	QJsonObject body;
	body["name"] = m_name;
	body["room"] = room.trimmed().toUpper();
	post("/api/join", body, SLOT(handleRoom()));
}

void NexarchOnline::post(const QString& path, const QJsonObject& body, const char* slot)
{
	if (base().isEmpty())
	{
		emit failed(tr("No server address was given."));
		return;
	}
	QNetworkRequest request(QUrl(base() + path));
	request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
	QNetworkReply* reply = m_net.post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));
	connect(reply, SIGNAL(finished()), this, slot);
}

void NexarchOnline::handleRoom()
{
	auto reply = qobject_cast<QNetworkReply*>(sender());
	if (reply == nullptr)
		return;
	reply->deleteLater();
	QJsonObject obj = replyJson(reply);
	QString error = errorText(reply, obj);
	if (!error.isEmpty())
	{
		emit failed(error);
		return;
	}
	m_room = obj.value("room").toString();
	m_token = obj.value("token").toString();
	m_color = obj.value("color").toString(m_color);
	applyState(obj.value("state").toObject(), true);
	emit ready();
}

void NexarchOnline::applyState(const QJsonObject& state, bool initial)
{
	if (state.isEmpty())
		return;
	if (state.contains("room"))
		m_room = state.value("room").toString(m_room);
	if (state.contains("count"))
		m_count = state.value("count").toInt(m_count);
	QString white = state.value("white").toString();
	QString black = state.value("black").toString();
	m_opponent = (m_color == "w") ? black : white;
	if (initial)
	{
		m_initialMoves.clear();
		const QJsonArray moves = state.value("moves").toArray();
		for (const QJsonValue& value : moves)
			m_initialMoves.append(value.toString());
	}
}

void NexarchOnline::startPolling()
{
	if (m_polling)
		return;
	m_polling = true;
	m_timer.start();
	poll();
}

void NexarchOnline::stopPolling()
{
	m_polling = false;
	m_timer.stop();
}

void NexarchOnline::poll()
{
	if (!m_polling || m_room.isEmpty())
		return;
	QUrl url(base() + "/api/state");
	QUrlQuery query;
	query.addQueryItem("room", m_room);
	query.addQueryItem("since", QString::number(m_count));
	url.setQuery(query);
	QNetworkReply* reply = m_net.get(QNetworkRequest(url));
	connect(reply, SIGNAL(finished()), this, SLOT(handleState()));
}

void NexarchOnline::handleState()
{
	auto reply = qobject_cast<QNetworkReply*>(sender());
	if (reply == nullptr)
		return;
	reply->deleteLater();
	QJsonObject obj = replyJson(reply);
	if (!errorText(reply, obj).isEmpty())
		return;
	QStringList moves;
	const QJsonArray array = obj.value("moves").toArray();
	for (const QJsonValue& value : array)
		moves.append(value.toString());
	applyState(obj, false);
	if (!moves.isEmpty())
		emit movesReceived(moves);
	if (obj.value("status").toString() == "finished")
	{
		stopPolling();
		emit gameOver(obj.value("result").toString());
	}
}

void NexarchOnline::sendMove(const QString& uci)
{
	if (m_room.isEmpty() || m_token.isEmpty() || uci.isEmpty())
		return;
	QJsonObject body;
	body["room"] = m_room;
	body["token"] = m_token;
	body["uci"] = uci;
	QNetworkRequest request(QUrl(base() + "/api/move"));
	request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
	QNetworkReply* reply = m_net.post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));
	connect(reply, SIGNAL(finished()), this, SLOT(handleMove()));
}

void NexarchOnline::handleMove()
{
	auto reply = qobject_cast<QNetworkReply*>(sender());
	if (reply == nullptr)
		return;
	reply->deleteLater();
	QJsonObject obj = replyJson(reply);
	if (!errorText(reply, obj).isEmpty())
		return;
	applyState(obj, false);
}

void NexarchOnline::reportResult(const QString& result)
{
	if (m_room.isEmpty() || m_token.isEmpty())
		return;
	QJsonObject body;
	body["room"] = m_room;
	body["token"] = m_token;
	body["result"] = result;
	QNetworkRequest request(QUrl(base() + "/api/end"));
	request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
	QNetworkReply* reply = m_net.post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));
	connect(reply, &QNetworkReply::finished, reply, &QNetworkReply::deleteLater);
}

NexarchOnlineDialog::NexarchOnlineDialog(QWidget* parent)
	: QDialog(parent),
	  m_online(new NexarchOnline(this)),
	  m_server(new QLineEdit("http://158.180.55.245:8090", this)),
	  m_name(new QLineEdit(this)),
	  m_room(new QLineEdit(this)),
	  m_color(new QComboBox(this)),
	  m_status(new QLabel(tr("Not connected"), this)),
	  m_create(new QPushButton(tr("Create room"), this)),
	  m_join(new QPushButton(tr("Join room"), this))
{
	setWindowTitle(tr("Play online"));
	m_name->setText(tr("Player"));
	m_color->addItem(tr("White"), "w");
	m_color->addItem(tr("Black"), "b");
	m_color->addItem(tr("Random"), "r");
	m_room->setPlaceholderText(tr("ABC123"));

	auto form = new QFormLayout;
	form->addRow(tr("Server"), m_server);
	form->addRow(tr("Your name"), m_name);
	form->addRow(tr("Color"), m_color);
	form->addRow(tr("Room code to join"), m_room);

	auto buttons = new QHBoxLayout;
	buttons->addWidget(m_create);
	buttons->addWidget(m_join);

	auto layout = new QVBoxLayout(this);
	layout->addLayout(form);
	layout->addLayout(buttons);
	layout->addWidget(m_status);
	auto closeBox = new QDialogButtonBox(QDialogButtonBox::Close, this);
	layout->addWidget(closeBox);

	connect(closeBox, &QDialogButtonBox::rejected, this, &QDialog::reject);
	connect(m_create, &QPushButton::clicked, this, &NexarchOnlineDialog::createRoom);
	connect(m_join, &QPushButton::clicked, this, &NexarchOnlineDialog::joinRoom);
	connect(m_online, &NexarchOnline::ready, this, &NexarchOnlineDialog::onReady);
	connect(m_online, &NexarchOnline::failed, this, &NexarchOnlineDialog::onFailed);
}

void NexarchOnlineDialog::createRoom()
{
	m_create->setEnabled(false);
	m_join->setEnabled(false);
	m_status->setText(tr("Creating room..."));
	m_online->createRoom(m_server->text(), m_name->text(), m_color->currentData().toString());
}

void NexarchOnlineDialog::joinRoom()
{
	if (m_room->text().trimmed().isEmpty())
	{
		m_status->setText(tr("Enter the room code first."));
		return;
	}
	m_create->setEnabled(false);
	m_join->setEnabled(false);
	m_status->setText(tr("Joining room..."));
	m_online->joinRoom(m_server->text(), m_name->text(), m_room->text());
}

void NexarchOnlineDialog::onReady()
{
	m_chosenColor = m_online->color();
	m_status->setText(tr("Room %1, you are %2.")
			  .arg(m_online->room(), m_chosenColor == "w" ? tr("White") : tr("Black")));
	accept();
}

void NexarchOnlineDialog::onFailed(const QString& message)
{
	m_create->setEnabled(true);
	m_join->setEnabled(true);
	m_status->setText(message);
}

NexarchOnline* NexarchOnlineDialog::takeOnline()
{
	NexarchOnline* online = m_online;
	m_online = nullptr;
	online->setParent(nullptr);
	return online;
}

QString NexarchOnlineDialog::color() const
{
	return m_chosenColor;
}

QStringList NexarchOnlineDialog::initialMoves() const
{
	return m_online ? m_online->initialMoves() : QStringList();
}

int NexarchOnlineDialog::initialCount() const
{
	return m_online ? m_online->initialCount() : 0;
}

NexarchRankingsDialog::NexarchRankingsDialog(QWidget* parent)
	: QDialog(parent),
	  m_table(new QTableWidget(this)),
	  m_status(new QLabel(tr("Loading live rankings..."), this))
{
	setWindowTitle(tr("Live rankings"));
	resize(640, 520);
	m_table->setColumnCount(5);
	m_table->setHorizontalHeaderLabels({tr("Rank"), tr("Player"), tr("Title"), tr("Rating"), tr("Site")});
	m_table->horizontalHeader()->setStretchLastSection(true);
	m_table->horizontalHeader()->setSectionResizeMode(1, QHeaderView::Stretch);
	m_table->setEditTriggers(QAbstractItemView::NoEditTriggers);
	m_table->setSelectionBehavior(QAbstractItemView::SelectRows);

	auto refresh = new QPushButton(tr("Refresh"), this);
	auto closeBox = new QDialogButtonBox(QDialogButtonBox::Close, this);
	auto buttons = new QHBoxLayout;
	buttons->addWidget(refresh);
	buttons->addStretch();
	buttons->addWidget(closeBox);

	auto layout = new QVBoxLayout(this);
	layout->addWidget(m_status);
	layout->addWidget(m_table);
	layout->addLayout(buttons);

	connect(refresh, &QPushButton::clicked, this, [=]()
	{
		m_table->setRowCount(0);
		m_status->setText(tr("Loading live rankings..."));
		loadLichess();
		loadChessCom();
	});
	connect(closeBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

	loadLichess();
	loadChessCom();
}

void NexarchRankingsDialog::loadLichess()
{
	QNetworkRequest request(QUrl("https://lichess.org/api/player/top/10/blitz"));
	request.setHeader(QNetworkRequest::UserAgentHeader, "CuteChess-NexarchRemake/1.0");
	QNetworkReply* reply = m_net.get(request);
	connect(reply, SIGNAL(finished()), this, SLOT(lichessReply()));
}

void NexarchRankingsDialog::loadChessCom()
{
	QNetworkRequest request(QUrl("https://api.chess.com/pub/leaderboards"));
	request.setHeader(QNetworkRequest::UserAgentHeader,
			  "Mozilla/5.0 (X11; Linux x86_64) CuteChess-NexarchRemake/1.0");
	QNetworkReply* reply = m_net.get(request);
	connect(reply, SIGNAL(finished()), this, SLOT(chessComReply()));
}

void NexarchRankingsDialog::lichessReply()
{
	auto reply = qobject_cast<QNetworkReply*>(sender());
	if (reply == nullptr)
		return;
	reply->deleteLater();
	QJsonObject obj = replyJson(reply);
	const QJsonArray users = obj.value("users").toArray();
	for (const QJsonValue& value : users)
	{
		QJsonObject user = value.toObject();
		QJsonObject perfs = user.value("perfs").toObject();
		QJsonObject blitz = perfs.value("blitz").toObject();
		int row = m_table->rowCount();
		m_table->insertRow(row);
		m_table->setItem(row, 0, new QTableWidgetItem(QString::number(row + 1)));
		m_table->setItem(row, 1, new QTableWidgetItem(user.value("username").toString()));
		m_table->setItem(row, 2, new QTableWidgetItem(user.value("title").toString()));
		m_table->setItem(row, 3, new QTableWidgetItem(QString::number(blitz.value("rating").toInt())));
		m_table->setItem(row, 4, new QTableWidgetItem("Lichess"));
	}
	if (users.isEmpty())
		m_status->setText(tr("Lichess rankings are unavailable right now."));
}

void NexarchRankingsDialog::chessComReply()
{
	auto reply = qobject_cast<QNetworkReply*>(sender());
	if (reply == nullptr)
		return;
	reply->deleteLater();
	QJsonObject obj = replyJson(reply);
	const QJsonArray users = obj.value("live_blitz").toArray();
	for (const QJsonValue& value : users)
	{
		QJsonObject user = value.toObject();
		int row = m_table->rowCount();
		m_table->insertRow(row);
		m_table->setItem(row, 0, new QTableWidgetItem(QString::number(user.value("rank").toInt())));
		m_table->setItem(row, 1, new QTableWidgetItem(user.value("username").toString()));
		m_table->setItem(row, 2, new QTableWidgetItem(user.value("title").toString()));
		m_table->setItem(row, 3, new QTableWidgetItem(QString::number(user.value("score").toInt())));
		m_table->setItem(row, 4, new QTableWidgetItem("Chess.com"));
	}
	if (!users.isEmpty())
		m_status->setText(tr("Live blitz rankings from Lichess and Chess.com."));
}

NexarchSettingsDialog::NexarchSettingsDialog(QWidget* parent)
	: QDialog(parent),
	  m_telemetry(new QCheckBox(tr("Send finished games anonymously"), this)),
	  m_strength(new QSlider(Qt::Horizontal, this)),
	  m_strengthLabel(new QLabel(this))
{
	setWindowTitle(tr("Nexarch settings"));
	m_telemetry->setChecked(Nexarch::telemetryEnabled());

	auto layout = new QVBoxLayout(this);

	auto strengthBox = new QGroupBox(tr("Engine strength"), this);
	auto strengthLayout = new QVBoxLayout(strengthBox);
	auto strengthRow = new QHBoxLayout;
	m_strength->setRange(10, 100);
	m_strength->setSingleStep(5);
	m_strength->setPageStep(10);
	m_strength->setValue(Nexarch::strength());
	m_strengthLabel->setMinimumWidth(150);
	m_strengthLabel->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
	auto updateStrengthLabel = [this](int percent)
	{
		m_strengthLabel->setText(percent >= 100
			? tr("Full strength")
			: tr("%1% strength").arg(percent));
	};
	connect(m_strength, &QSlider::valueChanged, this, updateStrengthLabel);
	updateStrengthLabel(m_strength->value());
	strengthRow->addWidget(m_strength, 1);
	strengthRow->addWidget(m_strengthLabel);
	strengthLayout->addLayout(strengthRow);
	auto strengthNote = new QLabel(tr("This is a handicap, not an Elo rating. Nexarch has no "
					 "measured rating yet. Lower values make it easier to beat, and the "
					 "setting applies to Nexarch engines in your next game."), this);
	strengthNote->setWordWrap(true);
	strengthLayout->addWidget(strengthNote);
	layout->addWidget(strengthBox);

	layout->addWidget(m_telemetry);
	auto note = new QLabel(tr("Off by default. When enabled, finished games are sent to the fixed "
				  "address below. No account name, email address or hardware ID is included."), this);
	note->setWordWrap(true);
	layout->addWidget(note);
	auto address = new QLabel(QString("<a href=\"%1\">%1</a>").arg(Nexarch::telemetryUrl()), this);
	address->setOpenExternalLinks(true);
	address->setTextInteractionFlags(Qt::TextBrowserInteraction);
	layout->addWidget(address);
	auto buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
	layout->addWidget(buttons);
	connect(buttons, &QDialogButtonBox::accepted, this, &NexarchSettingsDialog::save);
	connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
}

void NexarchSettingsDialog::save()
{
	Nexarch::setTelemetryEnabled(m_telemetry->isChecked());
	Nexarch::setStrength(m_strength->value());
	accept();
}

NexarchCreditsDialog::NexarchCreditsDialog(QWidget* parent)
	: QDialog(parent)
{
	setWindowTitle(tr("Credits"));
	resize(720, 620);
	auto text = new QTextBrowser(this);
	text->setOpenExternalLinks(true);
	text->setHtml(tr(
		"<h2>Cute Chess - Nexarch Remake</h2>"
		"<p>Nexarch is by Mark Ivanovskyy and is MIT licensed. This GUI is a modified build of "
		"<b>Cute Chess 1.5.1</b> by Ilari Pihlajisto, Arto Jonsson and contributors, GPL-3.0-or-later. "
		"The complete corresponding source is in <code>gui/cutechess-source</code> and at "
		"<a href=\"https://github.com/Markthegamer108/nexarch\">github.com/Markthegamer108/nexarch</a>.</p>"
		"<h3>Engines and networks</h3>"
		"<p>Stockfish 19, Reckless, Triumviratus, Berserk, Stormphrax, Obsidian, ShashChess, Cinder, "
		"Tarnished, Quanticade Cronus, Arasan, Raphael, Hobbes, Viridithas, Halogen, Integral, Caissa, "
		"Seer, pawnocchio, Astra, Devre, Clover, Renegade, PZChessBot, Maia 1900, PlentyChess, Coda, "
		"Alexandria, RubiChess, Koivisto, Ethereal and Lc0. Their licenses are listed in ENGINES.md "
		"and THIRD_PARTY.md. The BT4 network is by the Leela Chess Zero project.</p>"
		"<h3>Training data</h3>"
		"<p>Leela Chess Zero T80 data (ODbL/DbCL), the Lichess evaluation and fishnet databases (CC0), "
		"the Stockfish binpack collection (ODbL), and the UHO opening book (CC0). Nexarch's own "
		"conversions, manifests and evaluation sets are MIT unless the source requires otherwise.</p>"
		"<h3>Tools</h3>"
		"<p>PyTorch, NumPy, python-chess by Niklas Fiekas, Apache Arrow, Zstandard, the Kaggle CLI, "
		"Tomasz Sobczyk's binpack library, Qt 6, and the Cburnett piece set (CC BY-SA 3.0).</p>"
		"<h3>Compute and hosting</h3>"
		"<p>Kaggle for free GPUs and CPUs, GitHub for source and Actions, Hugging Face for datasets, "
		"and Oracle Cloud for the relay server.</p>"
		"<p>Thank you to everyone who released their work freely.</p>"));
	auto closeBox = new QDialogButtonBox(QDialogButtonBox::Close, this);
	connect(closeBox, &QDialogButtonBox::rejected, this, &QDialog::reject);
	auto layout = new QVBoxLayout(this);
	layout->addWidget(text);
	layout->addWidget(closeBox);
}

namespace Nexarch
{
QString telemetryUrl()
{
	return "http://158.180.55.245:8090/collect";
}

bool telemetryEnabled()
{
	return QSettings().value("nexarch/telemetry", false).toBool();
}

void setTelemetryEnabled(bool enabled)
{
	QSettings settings;
	settings.setValue("nexarch/telemetry", enabled);
	if (settings.value("nexarch/anonymous_id").toString().isEmpty())
		settings.setValue("nexarch/anonymous_id", QUuid::createUuid().toString(QUuid::WithoutBraces));
}

int strength()
{
	QSettings settings;
	if (settings.contains("nexarch/strength_percent"))
		return qBound(10, settings.value("nexarch/strength_percent", 100).toInt(), 100);
	if (settings.contains("nexarch/strength"))
	{
		const int elo = qBound(1320, settings.value("nexarch/strength").toInt(), 3190);
		return qBound(10, 10 + qRound((elo - 1320) * 90.0 / (3190 - 1320)), 100);
	}
	return 100;
}

void setStrength(int percent)
{
	QSettings().setValue("nexarch/strength_percent", qBound(10, percent, 100));
	applyStrength();
}

void applyStrength()
{
	auto* app = CuteChessApplication::instance();
	if (app == nullptr || app->engineManager() == nullptr)
		return;
	const int percent = strength();
	const int elo = 1320 + qRound((percent - 10) * (3190 - 1320) / 90.0);
	const int skill = qBound(0, qRound(percent / 5.0), 20);
	QList<EngineConfiguration> engines = app->engineManager()->engines();
	bool changed = false;
	for (EngineConfiguration& engine : engines)
	{
		if (!engine.name().contains("Nexarch", Qt::CaseInsensitive))
			continue;
		engine.setOption("UCI_LimitStrength", percent < 100);
		engine.setOption("UCI_Elo", elo);
		engine.setOption("Skill Level", skill);
		changed = true;
	}
	if (changed)
		app->engineManager()->setEngines(engines);
}

void sendGame(const QString& pgn, const QString& result)
{
	if (!telemetryEnabled() || pgn.isEmpty())
		return;
	QString clean;
	const QStringList lines = pgn.split('\n');
	for (const QString& line : lines)
	{
		if (line.startsWith("[White "))
			clean += "[White \"Anonymous\"]\n";
		else if (line.startsWith("[Black "))
			clean += "[Black \"Anonymous\"]\n";
		else if (line.startsWith("[Site "))
			clean += "[Site \"Cute Chess - Nexarch Remake\"]\n";
		else
			clean += line + "\n";
	}
	QSettings settings;
	QString id = settings.value("nexarch/anonymous_id").toString();
	if (id.isEmpty())
	{
		id = QUuid::createUuid().toString(QUuid::WithoutBraces);
		settings.setValue("nexarch/anonymous_id", id);
	}
	QJsonObject body;
	body["pgn"] = clean;
	body["result"] = result;
	body["anonymous_id"] = id;
	body["app"] = "Cute Chess - Nexarch Remake";
	body["version"] = QCoreApplication::applicationVersion();
	QUrl telemetryAddress(telemetryUrl());
	QNetworkRequest request(telemetryAddress);
	request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
	auto net = new QNetworkAccessManager(qApp);
	auto reply = net->post(request, QJsonDocument(body).toJson(QJsonDocument::Compact));
	QObject::connect(reply, &QNetworkReply::finished, net, &QObject::deleteLater);
}
}
